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
from plone.dexterity.content import Item
from plone.dexterity.fti import DexterityFTI
from plone.directives import form
from unittest2 import TestCase
from zope import schema
from zope.component import getSiteManager
from zope.interface import Interface
from zope.interface import implements
import transaction


class IAddress(Interface):
    pass


class IAddressSchema(form.Schema):

    address = schema.Text(title=u'Address', required=False)


class AddressLocationAdapter(object):

    def __init__(self, context):
        self.context = context

    def getLocationString(self):
        return self.context.address


class Address(Item):
    implements(IAddress, IGeoreferenceable)


class TestDexterityEvents(TestCase):

    layer = GEO_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)

        # Because we have a bug if we use ftw.geo in combination
        # with the IReferenceable behavior, we run all tests with
        # this behavior.
        fti = DexterityFTI(
            u'Address',
            schema='.'.join((IAddressSchema.__module__, 'IAddressSchema')),
            klass='.'.join((Address.__module__, 'Address')),
            behaviors=['plone.app.referenceablebehavior.referenceable.IReferenceable'])

        self.portal.portal_types._setObject('Address', fti)
        fti.lookupSchema()

        getSiteManager().registerAdapter(factory=AddressLocationAdapter,
                                         required=[IAddress],
                                         provided=IGeocodableLocation)

        transaction.commit()

    def tearDown(self):
        getSiteManager().unregisterAdapter(factory=AddressLocationAdapter,
                                           required=[IAddress],
                                           provided=IGeocodableLocation)

    @browsing
    def test_geocoding_triggered_when_creating_object(self, browser):
        browser.login().open()
        factoriesmenu.add('Address')
        with ExpectGeocodingRequest():
            browser.fill({'Address': 'Bern, Switzerland'}).submit()
        statusmessages.assert_no_error_messages()

        obj = self.portal.get('address')
        self.assertEquals(('Point', (7.444608, 46.947922)),
                          IGeoManager(obj).getCoordinates())

    @browsing
    def test_geocoding_triggered_when_editing(self, browser):
        browser.login().open()
        factoriesmenu.add('Address')
        with ExpectGeocodingRequest():
            browser.fill({'Address': 'Bern, Switzerland'}).submit()
        statusmessages.assert_no_error_messages()
        obj = self.portal.get('address')

        browser.find('Edit').click()
        with ExpectGeocodingRequest('Zurich, Switzerland', (8.53918, 47.36864)):
            browser.fill({'Address': 'Zurich, Switzerland'}).submit()

        self.assertEquals(('Point', (47.36864, 8.53918)),
                          IGeoManager(obj).getCoordinates())

    @browsing
    def test_delete_geocoding_if_address_removed(self, browser):
        browser.login().open()
        factoriesmenu.add('Address')
        with ExpectGeocodingRequest():
            browser.fill({'Address': 'Bern, Switzerland'}).submit()
        statusmessages.assert_no_error_messages()

        obj = self.portal.get('address')
        self.assertEquals(('Point', (7.444608, 46.947922)),
                          IGeoManager(obj).getCoordinates())

        browser.find('Edit').click()
        browser.fill({'Address': ''}).submit()

        self.assertEquals((None, None), IGeoManager(obj).getCoordinates())
