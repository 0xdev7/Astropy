# Licensed under a 3-clause BSD style license - see LICENSE.rst
from .. import misc

def test_pkg_finder():
    assert misc.find_current_module(0).__name__ == 'astropy.utils.misc'
    assert misc.find_current_module(1).__name__ == 'astropy.utils.tests.test_misc'