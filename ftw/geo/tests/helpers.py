from mocker import ARGS
from mocker import Expect
from mocker import KWARGS
from mocker import Mocker


class ExpectGeocodingRequest(object):
    """Mock geopy requests for geocoding a location.

    Example:

    with ExpectGeocodingRequest('Bern, Switzerland', (46.9479222, 7.444608499999999)):
        do_something()
    """

    def __init__(self, place='Bern, Switzerland', coords=(46.947922, 7.444608)):
        self.place = place
        self.coords = coords

    def __enter__(self):
        self.mocker = Mocker()
        expect = Expect(self.mocker)
        method = self.mocker.replace('ftw.geo.handlers.geocode_location')
        expect(method(ARGS, KWARGS)).result((self.place, self.coords, None))
        self.mocker.replay()

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type:
            self.mocker.verify()
            self.mocker.restore()
