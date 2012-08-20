from collective.geo.contentlocations.interfaces import IGeoManager
from collective.geo.geographer.interfaces import IGeoreferenceable
from collective.geo.geographer.interfaces import IGeoreferenced
from collective.geo.settings.interfaces import IGeoSettings
from ftw.geo.handlers import geocodeAddressHandler
from ftw.geo.interfaces import IGeocodableLocation
from ftw.geo.testing import ZCML_LAYER
from ftw.geo.tests.utils import is_coord_tuple
from ftw.testing import MockTestCase
from geopy.geocoders.google import GQueryError
from geopy.geocoders.google import GTooManyQueriesError
from mocker import ARGS
from mocker import KWARGS
from mocker import MATCH
from plone.registry.interfaces import IRegistry
from zope.annotation.interfaces import IAnnotations
from zope.component import adapts
from zope.component import getGlobalSiteManager
from zope.component import provideAdapter
from zope.component import queryAdapter
from zope.interface import implements
from zope.interface import Interface
from zope.interface.verify import verifyClass


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

    def replace_geopy_geocoders(self, result=None):
        """Replace the geocode_url method of the Google geocoder with a mock
        that doesn't actually send a request to the Google API.
        """

        if not result:
            # Use a default result
            result = (u'3012 Berne, Switzerland',
                      (46.958857500000001, 7.4273286000000001))

        self.request = self.mocker.mock()
        req_method = self.mocker.replace(
            'geopy.geocoders.google.Google.geocode_url')
        self.expect(req_method(ARGS, KWARGS)).call(
            self.request).count(0, None)
        self.expect(self.request(ARGS, KWARGS)).result(result)

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

    def mock_annotations(self, count=1):
        annotation_factory = self.mocker.mock()
        self.mock_adapter(annotation_factory, IAnnotations, (Interface,))
        self.expect(annotation_factory(self.context)
                   ).result({}).count(count)

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
                    ).result(geomanager_proxy)
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
        self.mock_context()
        self.mock_geomanager()
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()
        self.replay()

        event = self.mocker.mock()
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_same_location(self):
        # Use different address values for context to avoid caching
        self.mock_context('Hirschengraben', '3000', 'Bern', 'Switzerland')
        # geo manager should only be called once since the second request
        # won't cause a lookup
        self.mock_geomanager(count=1)
        self.mock_annotations(count=2)
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()
        self.replay()

        event = self.mocker.mock()
        # Call the handler twice with the same context, shouldn't cause a
        # lookup since location didn't change.
        geocodeAddressHandler(self.context, event)
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_api_key(self):
        # Use different address values for context to avoid caching
        self.mock_context('Bahnhofplatz', '3000', 'Bern', 'Switzerland')
        self.mock_geomanager()
        self.mock_annotations()
        self.mock_geosettings_registry(api_key='API_KEY_123')
        self.replace_geopy_geocoders()
        self.replay()

        event = self.mocker.mock()
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_invalid_location(self):
        self.mock_context('Bag End', '1234', 'The Shire', 'Middle Earth')
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()
        self.mocker.throw(GQueryError)
        self.replay()

        event = self.mocker.mock()
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_empty_location_string(self):
        self.mock_context('', '', '', '')
        self.mock_geosettings_registry()
        self.replay()

        event = self.mocker.mock()
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_missing_adapter(self):
        self.mock_context()
        # Unregister the IGeocodableLocation adapter
        gsm = getGlobalSiteManager()
        gsm.unregisterAdapter(SomeTypeLocationAdapter)
        self.replay()

        event = self.mocker.mock()
        # Handler should not fail even though there is no adapter
        geocodeAddressHandler(self.context, event)

    def test_geocoding_handler_with_too_many_queries(self):
        # Use different address values for context to avoid caching
        self.mock_context('Some Location', 'That', 'Wont', 'Matter')
        self.mock_annotations()
        self.mock_geosettings_registry()
        self.replace_geopy_geocoders()

        self.mocker.throw(GTooManyQueriesError)
        self.replay()

        event = self.mocker.mock()
        geocodeAddressHandler(self.context, event)
