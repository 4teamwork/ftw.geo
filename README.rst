Introduction
============

This product helps integrating the ``collective.geo.*`` packages and aims to
provide some sensible defaults. Besides some integration glue it defines a new
interface ``IGeocodableLocation`` that can be used to create adapters that knows
how to represent the location of a content type with address-like fields as a
string suitable for passing to a geocoding API.


Purpose
========

- Automatic geocoding of ``IGeoreferenceable`` content types via an
  ``IGeocodableLocation`` adapter
- Caching of geocoding responses
- Only trigger geocoding lookups if location related fields on the content item
  changed
- Facilitate doing automatic geocoding based on location fields and still allow
  for manually setting custom coordinates


Usage
=====


Automatically geocoding your content types
------------------------------------------

In order for your content types to be automatically geocoded on ``ObjectEdited``
or ``ObjectInitialized`` events, you need to create an adapter for your content
type that implements ``IGeocodableLocation`` and knows how to build a geocodable
location string from the content type's location related fields.

In order to implement the interface you need to define a ``getLocationString``
method on your adapter that returns the complete location as a comma separated
string, with the location parts getting less specific from left to right.

For example::

    '1600 Amphitheatre Parkway, Mountain View, CA, US'
    'Engehaldestr. 53, 3012 Bern, Switzerland'

If the ``getLocationString`` method returns the empty string or ``None``, the
event handler won't attempt to do a geocode lookup, so this is the suggested way
to abort geocoding if not enough location information is available.

Example code::

    from ftw.geo.interfaces import IGeocodableLocation
    from zope.component import adapts
    from zope.interface import implements


    class MyTypeLocationAdapter(object):
        """Adapter that is able to represent the location of an MyType in
        a geocodable string form.
        """
        implements(IGeocodableLocation)
        adapts(IMyType)

        def __init__(self, context):
            self.context = context

        def getLocationString(self):
            """Build a geocodable location string from the MyType's address
            related fields.
            """
            street = self.context.getAddress()
            zip_code = self.context.getZip()
            city = self.context.getCity()
            country = self.context.getCountry()

            location = ', '.join([street, zip_code, city, country])
            return location


Register the adapter with ZCML::

    <adapter
        factory=".mytpe.MyTypeLocationAdapter"
        />


Caching of geocoding responses
------------------------------

Responses from the geocoding API are being RAM cached. The cache key being used
is the result of the ``getLocationString`` method, which means that for every
unique location string the geocoding lookup is only done once and subsequently
fetched from the cache.


Only triggering geocoding when location fields changed
------------------------------------------------------

If we were to do a geocode lookup on every ``ObjectEdited`` event, any custom
coordinates that have been set would be overriden every time *any* field on
the content item is changed (even if the geocoding response itself was fetched
from the cache).

To avoid this, ``ftw.geo`` stores the result of ``getLocationString`` as an
annotation on the object and on ``ObjectEdited`` checks if the location string
(and therefore the location related fields) actually changed, and only does the
lookup when necessary. This means:

On ``ObjectInitialized`` the content type will first be geocoded initally
(unless ``getLocationString`` returned ``None`` or the empty string). If you
manually set coordinates after that through the 'Coordinates' tab provided by
``collective.geo.contentlocations`` they will be saved and overwrite the
coordinates determined previously by geocoding. After that, if you edit the
content item and change any fields *not* related to the location, the custom
coordinates will be preserved. Only if you change one of the location related
fields used in ``getLocationString`` the geocoding will be performed again and
any custom coordinates overwritten.


Google API Key
--------------

Google's geocoding API can be used without an API Key, but then is limited to
2500 requests per day. If you defined your Google Maps API Key in
``collective.geo.settings`` it will be used, otherwise the geocoding API will be
called without an API key.


Rendering a content map viewlet in a custom template
----------------------------------------------------

If you don't want your content map displayed in one of the default viewlet
managers (plone.abovecontentbody / plone.abovecontentbody) on the content item's
main view but instead in a custom view and/or a different viewlet manager, this
is how you do it:

First, you need to make sure your browser view implements a specific interface
and provide a KMLMapViewletLayer adapter (view, request, context, widget) for
it::

    <adapter
        for="..interfaces.IContactView
             zope.interface.Interface
             zope.interface.Interface
             zope.interface.Interface"
        factory="collective.geo.kml.browser.viewlets.KMLMapViewletLayers"
        />

Your view class have to provide the ``collective.geo.kml.interfaces.IKMLOpenLayersView``::

    from collective.geo.kml.interfaces import IKMLOpenLayersView
    from Products.Five.browser import BrowserView
    from zope.interface import implements


    class ContactView(BrowserView):
        implements(IKMLOpenLayersView)

Then, in your view's template, simply use the macros provided by
collective.geo.mapwidget::

        <div id="kml-content-viewlet">
          <metal:use use-macro="context/@@collectivegeo-macros/openlayers" />
          <metal:use use-macro="context/@@collectivegeo-macros/map-widget" />
        </div>



Dependencies
============

`collective.geo.settings <https://github.com/collective/collective.geo.settings>`_

`collective.geo.openlayers <https://github.com/collective/collective.geo.openlayers>`_

`collective.geo.geographer <https://github.com/collective/collective.geo.geographer>`_

`collective.geo.contentlocations <https://github.com/collective/collective.geo.contentlocations>`_

`collective.geo.kml <https://github.com/collective/collective.geo.kml>`_


If you're having trouble installing the collective.geo.* dependencies (namely
``libgeos`` and ``shapely``) trough your distribution's package manager, you can
build them yourself using this buildout configuration:



**shapely.cfg**::

    [buildout]
    parts +=
        geos
        shapely

    [geos]
    recipe = zc.recipe.cmmi
    url = http://download.osgeo.org/geos/geos-3.3.5.tar.bz2
    md5sum = 2ba61afb7fe2c5ddf642d82d7b16e75b
    extra_options =
        CC='gcc -m32'
        CXX='g++ -m32'

    [shapely]
    recipe = zc.recipe.egg:custom
    egg = Shapely
    include-dirs = ${geos:location}/include
    library-dirs = ${geos:location}/lib
    rpath = ${geos:location}/lib

Use it in your main ``buildout.cfg`` like this::

    [buildout]
    extends =
    #   ...
        shapely.cfg

    [instance1]
    eggs +=
        ${shapely:egg}

    environment-vars +=
        LD_LIBRARY_PATH ${geos:location}/lib


Links
=====

- Github: https://github.com/4teamwork/ftw.geo
- Issues: https://github.com/4teamwork/ftw.geo/issues
- Pypi: http://pypi.python.org/pypi/ftw.geo
- Continuous integration: https://jenkins.4teamwork.ch/search?q=ftw.geo


Contributors
============

- Lukas Graf [lukasg], Author


Copyright
=========

This package is copyright by `4teamwork <http://www.4teamwork.ch/>`_.

``ftw.geo`` is licensed under GNU General Public License, version 2.
