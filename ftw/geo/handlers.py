from collective.geo.contentlocations.interfaces import IGeoManager
from collective.geo.settings.interfaces import IGeoSettings
from ftw.geo.interfaces import IGeocodableLocation
from geopy import geocoders
from geopy.geocoders.google import GQueryError
from geopy.geocoders.google import GTooManyQueriesError
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.component import queryAdapter


LOCATION_KEY = 'ftw.geo.interfaces.IGeocodableLocation'


@ram.cache(lambda m, loc: loc)
def geocode_location(location):
    """Does a geocode lookup for `location` using the Google geocode API.
    """
    registry = getUtility(IRegistry)
    geo_settings = registry.forInterface(IGeoSettings)
    google_api_key = geo_settings.googleapi

    # Use Google API key if we have one, otherwise call geocoder
    # API without it (limited to 2500 lookups / day)
    if google_api_key:
        gmgeocoder = geocoders.Google(google_api_key)
    else:
        gmgeocoder = geocoders.Google()

    try:
        place, coords = gmgeocoder.geocode(location)
        return place, coords

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
                place, coords = geocoding_result
                geo_manager = queryAdapter(obj, IGeoManager)
                geo_manager.setCoordinates('Point', (coords[1], coords[0]))
                # Update the stored location
                ann[LOCATION_KEY] = location
