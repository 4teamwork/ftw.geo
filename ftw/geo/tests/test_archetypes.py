from Products.ATContentTypes.content.document import ATDocument
from Products.ATContentTypes.interfaces import IATDocument
from collective.geo.contentlocations.interfaces import IGeoManager
from collective.geo.geographer.interfaces import IGeoreferenceable
from ftw.geo.interfaces import IGeocodableLocation
from ftw.geo.testing import GEO_FUNCTIONAL_TESTING
from ftw.geo.tests.helpers import ExpectGeocodingRequest
from ftw.testbrowser import browsing
from ftw.testbrowser.pages import factoriesmenu
from ftw.testbrowser.pages import statusmessages
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import setRoles
from unittest2 import TestCase
from zope.component import getSiteManager
from zope.interface import classImplements
import transaction


class TitleLocationAdapter(object):
    """Use the title for geocoding in the test.
    """

    def __init__(self, context):
        self.context = context

    def getLocationString(self):
        return self.context.Title()


class TestArchetypesEvents(TestCase):

    layer = GEO_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)

        getSiteManager().registerAdapter(factory=TitleLocationAdapter,
                                         required=[IATDocument],
                                         provided=IGeocodableLocation)
        classImplements(ATDocument, IGeoreferenceable)
        transaction.commit()

    def tearDown(self):
        getSiteManager().unregisterAdapter(factory=TitleLocationAdapter,
                                           required=[IATDocument],
                                           provided=IGeocodableLocation)
        transaction.commit()

    @browsing
    def test_geocoding_triggered_when_creating_object(self, browser):
        browser.login().open()
        factoriesmenu.add('Page')
        with ExpectGeocodingRequest():
            browser.fill({'Title': 'Bern, Switzerland'}).submit()
        statusmessages.assert_no_error_messages()

        obj = self.portal.get('bern-switzerland')
        self.assertEquals(('Point', (7.444608, 46.947922)),
                          IGeoManager(obj).getCoordinates())

    @browsing
    def test_geocoding_triggered_when_editing_address(self, browser):
        browser.login().open()
        factoriesmenu.add('Page')
        with ExpectGeocodingRequest():
            browser.fill({'Title': 'Bern, Switzerland'}).submit()
        statusmessages.assert_no_error_messages()
        obj = self.portal.get('bern-switzerland')

        browser.find('Edit').click()
        with ExpectGeocodingRequest('Zurich, Switzerland', (8.53918, 47.36864)):
            browser.fill({'Title': 'Zurich, Switzerland'}).submit()

        self.assertEquals(('Point', (47.36864, 8.53918)),
                          IGeoManager(obj).getCoordinates())

    @browsing
    def test_delete_geocoding_if_address_removed(self, browser):
        browser.login().open()
        factoriesmenu.add('Page')

        with ExpectGeocodingRequest():
            browser.fill({'Title': 'Bern, Switzerland'}).submit()

        statusmessages.assert_no_error_messages()
        obj = self.portal.get('bern-switzerland')
        obj.schema.get('title').required = False

        browser.find('Edit').click()
        browser.fill({'Title': ''}).submit()

        self.assertEquals((None, None), IGeoManager(obj).getCoordinates())
