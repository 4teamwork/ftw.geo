# pylint: disable=E0211
# E0211: Method has no argument

from zope.interface import Interface
from zope.viewlet.interfaces import IViewletManager


class IGeocodableLocation(Interface):
    """Interface used to implement an adapter that is able to represent a
    content item's location as a geocodable string.

    In order for content types to be automatically geocoded on ``ObjectEdited``
    or ``ObjectInitialized`` events, there must be an adapter for the content
    type that implements ``IGeocodableLocation`` and knows how to build a
    geocodable location string from the content type's location related fields.

    In order to implement the interface the adapter needs to define a
    ``getLocationString`` method that returns the complete location as a comma
    separated string, with the location parts getting less specific from
    left to right.

    For example:

        '1600 Amphitheatre Parkway, Mountain View, CA, US'
        'Engehaldestr. 53, 3012 Bern, Switzerland'

    If the ``getLocationString`` method returns the empty string or ``None``,
    the event handler won't attempt to do a geocode lookup, so this is the
    suggested way to abort geocoding if not enough location information is
    available.
    """

    def getLocationString():
        """Build a geocodable location string from the content type's location
        related fields.
        """


class IContentMapViewletManager(IViewletManager):
    """A viewlet manager that renders a map for a Georeferenceable content.
    """
