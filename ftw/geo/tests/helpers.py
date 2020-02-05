from contextlib import contextmanager
from mock import patch


@contextmanager
def ExpectGeocodingRequest(place='Bern, Switzerland', coords=(46.947922, 7.444608)):

    with patch('ftw.geo.handlers.geocode_location') as mocked_geocode_location:
        mocked_geocode_location.return_value = (place, coords, None)
        yield
