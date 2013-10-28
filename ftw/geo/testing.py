from ftw.testing.layer import ComponentRegistryLayer
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.testing import zca
from zope.configuration import xmlconfig


class ZCMLLayer(ComponentRegistryLayer):
    """A layer which only sets up the zcml, but does not start a zope
    instance.
    """

    defaultBases = (zca.ZCML_DIRECTIVES,)

    def setUp(self):
        super(ZCMLLayer, self).setUp()
        import ftw.geo.tests
        self.load_zcml_file('test.zcml', ftw.geo.tests)


ZCML_LAYER = ZCMLLayer()


class GeoLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        xmlconfig.string(
            '<configure xmlns="http://namespaces.zope.org/zope">'
            '  <include package="z3c.autoinclude" file="meta.zcml" />'
            '  <includePlugins package="plone" />'
            '  <includePluginsOverrides package="plone" />'
            '</configure>',
            context=configurationContext)


    def setUpPloneSite(self, portal):
        applyProfile(portal, 'plone.app.dexterity:default')


GEO_FIXTURE = GeoLayer()
GEO_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(GEO_FIXTURE, ),
    name="ftw.geo:functional")
