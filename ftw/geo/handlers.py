from collective.geo.contentlocations.interfaces import IGeoManager
from ftw.geo import _
from ftw.geo.interfaces import IGeocodableLocation
from geopy import geocoders
from geopy.geocoders.google import GQueryError
from geopy.geocoders.google import GTooManyQueriesError
from plone.memoize import ram
from Products.statusmessages.interfaces import IStatusMessage
from zope.annotation.interfaces import IAnnotations
from zope.component import queryAdapter


LOCATION_KEY = 'ftw.geo.interfaces.IGeocodableLocation'


@ram.cache(lambda m, loc: loc)
def geocode_location(location):
    """Does a geocode lookup for `location` using the Google geocode API and
    returns a 3-tuple (place, coords, msg).

    If more than one result has been found, the first one is selected and
    `msg` will contain a status message telling the user which place has
    been selected.
    """
    msg = None

    # Google map api v3 does not take any api key
    # Check GoogleV3 implementation
    gmgeocoder = geocoders.GoogleV3()

    try:
        results = list(gmgeocoder.geocode(location, exactly_one=False))
        place, coords = results[0]
        if len(results) > 1:
            msg= _(u'More than one location found, chose first match '
                    '"${place}". Please check that coordinates are correct.',
                    mapping=dict(place=place))
        return (place, coords, msg)

    except GQueryError:
        # Couldn't find a suitable location
        return
    except GTooManyQueriesError:
        # Query limit has been reached
        return


def geocodeAddressHandler(obj, event):
    """Handler to automatically do geocoding lookups for IGeoreferenceable
    objects that have an IGeocodableLocation adapter.
    """

    location_adapter = queryAdapter(obj, IGeocodableLocation)
    if not location_adapter:
        return

    location = location_adapter.getLocationString()

    if location:
        ann = queryAdapter(obj, IAnnotations)
        previous_location = ann.get(LOCATION_KEY)
        # Only do the geocoding lookup if the location changed
        if not location == previous_location:
            geocoding_result = geocode_location(location)
            if geocoding_result:
                place, coords, msg = geocoding_result
                if msg:
                    status = IStatusMessage(obj.REQUEST)
                    status.addStatusMessage(msg, type='info')
                geo_manager = queryAdapter(obj, IGeoManager)
                geo_manager.setCoordinates('Point', (coords[1], coords[0]))
                # Update the stored location
                ann[LOCATION_KEY] = location
