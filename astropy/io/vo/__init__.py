from __future__ import division, absolute_import

# If we're in the source directory, don't import anything, since that
# requires 2to3 to be run.
from astropy import setup_helpers
if setup_helpers.is_in_build_mode():
    pass
else:
    del setup_helpers
    from .exceptions import *
