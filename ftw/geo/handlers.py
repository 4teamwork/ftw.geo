from collective.geo.contentlocations.interfaces import IGeoManager
from ftw.geo import _
from ftw.geo.interfaces import IGeocodableLocation
from geopy import geocoders
from geopy.geocoders.googlev3 import GQueryError
from geopy.geocoders.googlev3 import GTooManyQueriesError
from plone.memoize import ram
from Products.statusmessages.interfaces import IStatusMessage
from urllib2 import URLError
from ZODB.POSException import ConflictError
from zope.annotation.interfaces import IAnnotations
from zope.component import queryAdapter
from zope.component.hooks import getSite


LOCATION_KEY = 'ftw.geo.interfaces.IGeocodableLocation'


def display_status_message(msg):
    site = getSite()
    status = IStatusMessage(site.REQUEST)
    status.addStatusMessage(msg, type='info')


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
            msg = _(u'msg_multiple_matches',
                    default=u'More than one location found, chose first match '
                    '"${place}". Please check that coordinates are correct.',
                    mapping=dict(place=place))
        return (place, coords, msg)

    except GQueryError:
        # Couldn't find a suitable location
        msg = _(u'msg_no_match',
                default=u'Couldn\'t find a suitable match for location '
                '"${location}". Please use the "coordinates" tab to manually '
                'set the correct map loaction.',
                mapping=dict(location=location))
        display_status_message(msg)
        return

    except GTooManyQueriesError:
        msg = _(u'msg_too_many_queries',
                default=u'Geocoding failed because daily query limit has '
                'been exceeded.')
        display_status_message(msg)
        return

    except URLError:
        msg = _(u'msg_network_error',
                default=u'Geocoding failed because of a network error.')
        display_status_message(msg)

    except ConflictError:
        raise

    except Exception, e:
        msg = _(u'msg_unhandled_exception',
                default=u'Geocoding failed because of an error: ${exception}',
                mapping=dict(exception=e))
        display_status_message(msg)
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
                _place, coords, msg = geocoding_result
                if msg:
                    display_status_message(msg)
                geo_manager = queryAdapter(obj, IGeoManager)
                geo_manager.setCoordinates('Point', (coords[1], coords[0]))
                # Update the stored location
                ann[LOCATION_KEY] = location
