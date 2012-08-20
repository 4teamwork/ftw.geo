"""
Various utils used in ftw.geo tests
"""


def is_coord_tuple(value):
    """Check if `value` is a coordinate tuple, like for example
    (7.4273286000000001, 46.958857500000001)
    """
    if isinstance(value, tuple) and len(value) == 2:
        if isinstance(value[0], float) and \
           isinstance(value[1], float):
            return True
    return False