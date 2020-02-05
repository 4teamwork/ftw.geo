from collective.geo.contentlocations.interfaces import IGeoManager
from collective.geo.geographer.interfaces import IGeoreferenceable
from collective.geo.geographer.interfaces import IGeoreferenced
from contextlib import contextmanager
from ftw.geo.handlers import geocodeAddressHandler
from ftw.geo.interfaces import IGeocodableLocation
from ftw.geo.testing import ZCML_LAYER
from ftw.testing import MockTestCase
from mock import patch
from plone import api
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

        self.original_get_registry_record = api.portal.get_registry_record
        api.portal.get_registry_record = lambda *args, **kwargs: 'mock tests deserve this'
        self.mock_site()
        self.mock_statusmessage_adapter()
        self.mock_annotations()

    def tearDown(self):
        super(TestGeocoding, self).tearDown()
        self.context = None
        # Invalidate the geocoding cache so tests run in isolation
        ram.global_cache.invalidate('ftw.geo.handlers.geocode_location')

        api.portal.get_registry_record = self.original_get_registry_record

    @contextmanager
    def replace_geopy_geocoders(self, result=None):
        if not result:
            # Use a default result
            result = ((u'3012 Berne, Switzerland',
                      (46.958857500000001, 7.4273286000000001)), )
        with patch('geopy.geocoders.googlev3.GoogleV3.geocode') as mocked_geocode:
            mocked_geocode.return_value = result
            yield

    def mock_site(self):
        site = self.create_dummy(getSiteManager=getGlobalSiteManager,
                                 REQUEST=self.stub_request())
        setSite(site)

    def mock_statusmessage_adapter(self):
        status = self.mock()
        factory = self.mock()
        factory.return_value = status
        self.message_cache = self.create_dummy()

        status.addStatusMessage.side_effect = lambda msg, type: setattr(self.message_cache, type, msg)
        self.mock_adapter(factory, IStatusMessage, (Interface, ))

    def mock_context(self, address='Engehaldestr. 53',
                     zip_code='3012',
                     city='Bern',
                     country='Switzerland'):
        ifaces = [ISomeType, IGeoreferenceable, IAnnotations, IGeoreferenced]
        self.context = self.providing_stub(ifaces)
        self.context.getAddress.return_value = address
        self.context.getZip.return_value = zip_code
        self.context.getCity.return_value = city
        self.context.getCountry.return_value = country

        request = self.stub_request()
        self.context.REQUEST.return_value = request

    def mock_annotations(self):
        self.annotation_factory = self.mock()
        self.annotation_factory.return_value = {}
        self.mock_adapter(self.annotation_factory, IAnnotations, (Interface,))

    def mock_geosettings_registry(self, api_key=None):
        registry = self.stub()
        self.mock_utility(registry, IRegistry)
        proxy = self.stub()
        registry.forInterface.return_value = proxy
        proxy.googleapi.return_value = api_key

    def mock_geomanager(self):
        self.geomanager_proxy = self.mock()
        self.geomanager_factory = self.mock()
        self.geomanager_factory.return_value = self.geomanager_proxy
        self.mock_adapter(self.geomanager_factory, IGeoManager, (Interface,))

    def test_geocoding_adapter(self):
        self.mock_context()

        location_adapter = queryAdapter(self.context, IGeocodableLocation)
        self.assertTrue(location_adapter is not None)

        loc_string = location_adapter.getLocationString()
        self.assertEquals(loc_string,
                          'Engehaldestr. 53, 3012, Bern, Switzerland')

        verifyClass(IGeocodableLocation, SomeTypeLocationAdapter)

    def test_geocoding_handler(self):
        self.mock_context()
        self.mock_geomanager()
        self.mock_geosettings_registry()
        event = self.mock()
        with self.replace_geopy_geocoders():
            geocodeAddressHandler(self.context, event)
        self.assertEqual(self.annotation_factory.call_count, 1)

    def test_geocoding_handler_with_same_location(self):
        # Use different address values for context to avoid caching
        self.mock_context('Hirschengraben', '3000', 'Bern', 'Switzerland')
        # geo manager should only be called once since the second request
        # won't cause a lookup
        self.mock_geomanager()
        self.mock_geosettings_registry()
        event = self.mock()

        # Call the handler twice with the same context, shouldn't cause a
        # lookup since location didn't change.
        with self.replace_geopy_geocoders():
            geocodeAddressHandler(self.context, event)
            geocodeAddressHandler(self.context, event)

        self.assertEqual(self.annotation_factory.call_count, 2)
        self.assertEqual(self.geomanager_proxy.setCoordinates.call_count, 1)

    def test_geocoding_handler_with_api_key(self):
        # Use different address values for context to avoid caching
        self.mock_context('Bahnhofplatz', '3000', 'Bern', 'Switzerland')
        self.mock_geomanager()
        self.mock_geosettings_registry(api_key='API_KEY_123')
        event = self.mock()
        with self.replace_geopy_geocoders():
            geocodeAddressHandler(self.context, event)
        self.assertEqual(self.annotation_factory.call_count, 1)

    def test_geocoding_handler_with_invalid_location(self):
        self.mock_context('Bag End', '1234', 'The Shire', 'Middle Earth')
        self.mock_geosettings_registry()
        event = self.mock()
        with patch('geopy.geocoders.googlev3.GoogleV3.geocode') as mocked_geocode:
            mocked_geocode.side_effect = GeocoderQueryError()
            geocodeAddressHandler(self.context, event)

        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_no_match')
        self.assertEqual(self.annotation_factory.call_count, 1)

    def test_geocoding_handler_with_invalid_non_ascii_locatio(self):
        self.mock_context('Ober\xc3\xa4geri', '1234', 'The Shire', 'Middle Earth')
        event = self.mock()
        with patch('geopy.geocoders.googlev3.GoogleV3.geocode') as mocked_geocode:
            mocked_geocode.side_effect = GeocoderQueryError()
            geocodeAddressHandler(self.context, event)

        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_no_match')
        self.assertEqual(self.annotation_factory.call_count, 1)

        msg = self.message_cache.info
        loc = msg.mapping['location']
        # Concatenate message (unicode) and location to force a possible
        # UnicodeDecodeError if string types don't match
        self.assertIsInstance(msg + loc, unicode)

    def test_geocoding_handler_with_empty_location_string(self):
        self.mock_context('', '', '', '')
        self.mock_geosettings_registry()
        event = self.mock()
        geocodeAddressHandler(self.context, event)
        self.assertEqual(self.annotation_factory.call_count, 0)

    def test_geocoding_handler_with_missing_adapter(self):
        self.mock_context()
        # Unregister the IGeocodableLocation adapter
        gsm = getGlobalSiteManager()
        gsm.unregisterAdapter(SomeTypeLocationAdapter)
        event = self.mock()

        # Handler should not fail even though there is no adapter
        geocodeAddressHandler(self.context, event)
        self.assertEqual(self.annotation_factory.call_count, 0)

    def test_geocoding_handler_with_too_many_queries(self):
        self.mock_context('Some Address')
        self.mock_geosettings_registry()
        event = self.mock()
        with patch('geopy.geocoders.googlev3.GoogleV3.geocode') as mocked_geocode:
            mocked_geocode.side_effect = GeocoderQuotaExceeded()
            geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_too_many_queries')
        self.assertEqual(self.annotation_factory.call_count, 1)

    def test_multiple_results(self):
        self.mock_context('Hasslerstrasse', '3000', 'Bern', 'Switzerland')
        self.mock_geomanager()
        self.mock_geosettings_registry()

        result = ((u'3001 Berne, Switzerland',
                   (46.958857500000001, 7.4273286000000001)),
                  (u'3000 Berne, Switzerland',
                   (46.958857500000002, 7.4273286000000002)), )
        with self.replace_geopy_geocoders(result=result):
            geocodeAddressHandler(self.context, None)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_multiple_matches')
        self.assertEqual(self.annotation_factory.call_count, 1)

    def test_geocoding_handler_with_network_error(self):
        self.mock_context('Some Address')
        self.mock_geosettings_registry()
        event = self.mock()

        with patch('geopy.geocoders.googlev3.GoogleV3.geocode') as mocked_geocode:
            mocked_geocode.side_effect = URLError('foo')
            geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_network_error')
        self.assertEqual(self.annotation_factory.call_count, 1)

    def test_geocoding_doesnt_swallow_conflict_error(self):
        self.mock_context('Some Address')
        self.mock_geosettings_registry()
        event = self.mock()
        with patch('geopy.geocoders.googlev3.GoogleV3.geocode') as mocked_geocode:
            mocked_geocode.side_effect = ConflictError()
            # Make sure ConflictError always gets raised
            with self.assertRaises(ConflictError):
                geocodeAddressHandler(self.context, event)
        self.assertEqual(self.annotation_factory.call_count, 1)

    def test_geocoding_unhandled_exception(self):
        self.mock_context('Some Address')
        self.mock_geosettings_registry()
        event = self.mock()
        with patch('geopy.geocoders.googlev3.GoogleV3.geocode') as mocked_geocode:
            mocked_geocode.side_effect = Exception('Something broke!')
            geocodeAddressHandler(self.context, event)
        # Expect the appropriate info message
        self.assertEquals(self.message_cache.info, 'msg_unhandled_exception')
        self.assertEqual(self.annotation_factory.call_count, 1)
