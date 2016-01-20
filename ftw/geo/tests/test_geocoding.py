from collective.geo.contentlocations.interfaces import IGeoManager
from collective.geo.geographer.interfaces import IGeoreferenceable
from collective.geo.geographer.interfaces import IGeoreferenced
from collective.geo.settings.interfaces import IGeoSettings
from ftw.geo.handlers import geocodeAddressHandler
from ftw.geo.interfaces import IGeocodableLocation
from ftw.geo.testing import ZCML_LAYER
from ftw.geo.tests.utils import is_coord_tuple
from ftw.testing import MockTestCase
from mocker import ANY
from mocker import ARGS
from mocker import KWARGS
from mocker import MATCH
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from Products.statusmessages.interfaces import IStatusMessage
from urllib2 import URLError
from ZODB.POSException import ConflictError
from zope.annotation.interfaces import IAnnotations
from zope.component import adapts
from zope.component import getGlobalSiteManager
from zope.component import provideAdapter
from zope.component import queryAdapter
from zope.component.hooks import setSite
from zope.interface import implements
from zope.interface import Interface
from zope.interface.verify import verifyClass


try:
    # geopy < 0.96
    from geopy.geocoders.googlev3 import GQueryError
    from geopy.geocoders.googlev3 import GTooManyQueriesError
    GeocoderQueryError = GQueryError
    GeocoderQuotaExceeded = GTooManyQueriesError
except ImportError:
    # geopy >= 0.96
    from geopy.exc import GeocoderQueryError
    from geopy.exc import GeocoderQuotaExceeded


class ISomeType(Interface):
    pass


class SomeTypeLocationAdapter(object):
    """Adapter that is able to represent the location of a SomeType in
    a geocodable string form.
    """
    implements(IGeocodableLocation)
    adapts(ISomeType)

    def __init__(self, context):
        self.context = context

    def getLocationString(self):
        """Build a geocodable location string from SomeType's address
        related fields.
        """
        street = self.context.getAddress()
        zip_code = self.context.getZip()
        city = self.context.getCity()
        country = self.context.getCountry()

        if not (street or zip_code or city):
            # Not enough location information to do sensible geocoding
            return ''

        location = ', '.join([street, zip_code, city, country])
        return location


class TestGeocoding(MockTestCase):

    layer = ZCML_LAYER

    def setUp(self):
        super(TestGeocoding, self).setUp()
        provideAdapter(SomeTypeLocationAdapter)
        self.context = None

    def tearDown(self):
        super(TestGeocoding, self).tearDown()
        self.context = None
        # Invalidate the geocoding cache so tests run in isolation
        ram.global_cache.invalidate('ftw.geo.handlers.geocode_location')

    def replace_geopy_geocoders(self, result=None):
        """Replace the geocode method of the Google geocoder with a mock
        that doesn't actually send a request to the Google API.
        """

        if not result:
            # Use a default result
            result = ((u'3012 Berne, Switzerland',
                      (46.958857500000001, 7.4273286000000001)), )

        self.request = self.mocker.mock()
        req_method = self.mocker.replace(
            'geopy.geocoders.googlev3.GoogleV3.geocode')
        self.expect(req_method(ARGS, KWARGS)).call(
            self.request).count(0, None)
        self.expect(self.request(ARGS, KWARGS)).result(result)

    def mock_site(self):
        site = self.create_dummy(getSiteManager=getGlobalSiteManager,
                                 REQUEST=self.stub_request())
        setSite(site)

    def mock_statusmessage_adapter(self):
        self.statusmsg = self.mocker.mock(count=False)
        self.message_cache = self.create_dummy()
        self.expect(self.statusmsg(ANY).addStatusMessage(ANY, type=ANY)).call(
            lambda msg, type: setattr(self.message_cache, type, msg))
        self.mock_adapter(self.statusmsg, IStatusMessage, (Interface, ))

    def mock_context(self, address='Engehaldestr. 53',
                     zip_code='3012',
                     city='Bern',
                     country='Switzerland'):
        ifaces = [ISomeType, IGeoreferenceable, IAnnotations, IGeoreferenced]
        self.context = self.providing_stub(ifaces)
        self.expect(self.context.getAddress()).result(address)
        self.expect(self.context.getZip()).result(zip_code)
        self.expect(self.context.getCity()).result(city)
        self.expect(self.context.getCountry()).result(country)

        request = self.stub_request()
        self.expect(self.context.REQUEST).result(request)

    def mock_annotations(self, count=1):
        annotation_factory = self.mocker.mock()
        self.mock_adapter(annotation_factory, IAnnotations, (Interface,))
        self.expect(annotation_factory(self.context)).result({}).count(count)

    def mock_geosettings_registry(self, api_key=None):
        registry = self.stub()
        self.mock_utility(registry, IRegistry)
        proxy = self.stub()
        self.expect(registry.forInterface(IGeoSettings)).result(proxy)
        self.expect(proxy.googleapi).result(api_key)

    def mock_geomanager(self, count=1):
        geomanager_proxy = self.stub()
        geomanager_factory = self.mocker.mock()
        self.mock_adapter(geomanager_factory, IGeoManager, (Interface,))
        self.expect(geomanager_factory(self.context)
                    ).result(geomanager_proxy).count(0, None)
        coords = ('Point', MATCH(is_coord_tuple))
        self.expect(geomanager_proxy.setCoordinates(*coords)).count(count)

    def test_geocoding_adapter(self):
        self.mock_context()
        self.replay()

        location_adapter = queryAdapter(self.context, IGeocodableLocation)
        self.assertTrue(location_adapter is not None)

        loc_string = location_adapter.getLocationString()
        self.assertEquals(loc_string,
                          'Engehaldestr. 53, 3012, Bern, Switzerland')

        verifyClass(IGeocodableLocation, SomeTypeLocationAdapter)

    def test_geocoding_handler(self):
        self.mock_site()
        self.mock_context()
        self.mock_geomanager()
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()
        self.replay()

        event = self.mocker.mock()
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_same_location(self):
        self.mock_site()
        # Use different address values for context to avoid caching
        self.mock_context('Hirschengraben', '3000', 'Bern', 'Switzerland')
        # geo manager should only be called once since the second request
        # won't cause a lookup
        self.mock_geomanager(count=1)
        self.mock_annotations(count=2)
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()
        event = self.mocker.mock()
        self.replay()

        # Call the handler twice with the same context, shouldn't cause a
        # lookup since location didn't change.
        geocodeAddressHandler(self.context, event)
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_api_key(self):
        self.mock_site()
        # Use different address values for context to avoid caching
        self.mock_context('Bahnhofplatz', '3000', 'Bern', 'Switzerland')
        self.mock_geomanager()
        self.mock_annotations()
        self.mock_geosettings_registry(api_key='API_KEY_123')
        self.replace_geopy_geocoders()
        event = self.mocker.mock()
        self.replay()

        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_invalid_location(self):
        self.mock_site()
        self.mock_statusmessage_adapter()
        self.mock_context('Bag End', '1234', 'The Shire', 'Middle Earth')
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()
        self.mocker.throw(GeocoderQueryError)
        event = self.mocker.mock()
        self.replay()

        geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_no_match')

    def test_geocoding_handler_with_invalid_non_ascii_locatio(self):
        self.mock_site()
        self.mock_statusmessage_adapter()
        self.mock_context('Ober\xc3\xa4geri', '1234', 'The Shire', 'Middle Earth')
        self.mock_annotations()
        self.replace_geopy_geocoders()
        self.mocker.throw(GeocoderQueryError)
        event = self.mocker.mock()
        self.replay()

        geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_no_match')

        msg = self.message_cache.info
        loc = msg.mapping['location']
        # Concatenate message (unicode) and location to force a possible
        # UnicodeDecodeError if string types don't match
        self.assertIsInstance(msg + loc, unicode)

    def test_geocoding_handler_with_empty_location_string(self):
        self.mock_site()
        self.mock_context('', '', '', '')
        self.mock_geosettings_registry()
        event = self.mocker.mock()
        self.replay()

        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_missing_adapter(self):
        self.mock_site()
        self.mock_context()
        # Unregister the IGeocodableLocation adapter
        gsm = getGlobalSiteManager()
        gsm.unregisterAdapter(SomeTypeLocationAdapter)
        event = self.mocker.mock()
        self.replay()

        # Handler should not fail even though there is no adapter
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_too_many_queries(self):
        self.mock_site()
        self.mock_statusmessage_adapter()
        self.mock_context('Some Address')
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()

        self.mocker.throw(GeocoderQuotaExceeded)
        event = self.mocker.mock()
        self.replay()

        geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_too_many_queries')

    def test_multiple_results(self):
        self.mock_site()
        self.mock_statusmessage_adapter()
        self.mock_context('Hasslerstrasse', '3000', 'Bern', 'Switzerland')
        self.mock_geomanager()
        self.mock_annotations()
        self.mock_geosettings_registry()

        result = ((u'3001 Berne, Switzerland',
                   (46.958857500000001, 7.4273286000000001)),
                  (u'3000 Berne, Switzerland',
                   (46.958857500000002, 7.4273286000000002)), )
        self.replace_geopy_geocoders(result=result)
        self.replay()

        geocodeAddressHandler(self.context, None)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_multiple_matches')

    def test_geocoding_handler_with_network_error(self):
        self.mock_site()
        self.mock_statusmessage_adapter()
        self.mock_context('Some Address')
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()

        event = self.mocker.mock()
        self.mocker.throw(URLError('foo'))
        self.replay()

        geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_network_error')

    def test_geocoding_doesnt_swallow_conflict_error(self):
        self.mock_site()
        self.mock_context('Some Address')
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()

        self.mocker.throw(ConflictError)
        event = self.mocker.mock()
        self.replay()

        # Make sure ConflictError always gets raised
        with self.assertRaises(ConflictError):
            geocodeAddressHandler(self.context, event)

    def test_geocoding_unhandled_exception(self):
        self.mock_site()
        self.mock_statusmessage_adapter()
        self.mock_context('Some Address')
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()

        event = self.mocker.mock()
        self.mocker.throw(Exception('Something broke!'))
        self.replay()

        geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_unhandled_exception')
