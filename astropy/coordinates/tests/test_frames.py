# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import numpy as np
from numpy.testing import assert_allclose

from ... import units as u
from ...tests.helper import pytest
from .. import  representation

def test_create_data_frames():
    from ..builtin_frames import ICRS

    #from repr
    i1 = ICRS(representation.SphericalRepresentation(1*u.deg, 2*u.deg, 3*u.kpc))
    i2 = ICRS(representation.UnitSphericalRepresentation(lon=1*u.deg, lat=2*u.deg))

    #from preferred name
    i3 = ICRS(ra=1*u.deg, dec=2*u.deg, distance=3*u.kpc)
    i4 = ICRS(ra=1*u.deg, dec=2*u.deg)

    assert i1.data.lat == i3.data.lat
    assert i1.data.lon == i3.data.lon
    assert i1.data.distance == i3.data.distance

    assert i2.data.lat == i4.data.lat
    assert i2.data.lon == i4.data.lon

    #now make sure the preferred names work as properties
    assert_allclose(i1.ra, i3.ra)
    assert_allclose(i2.ra, i4.ra)
    assert_allclose(i1.distance, i3.distance)

    with pytest.raises(AttributeError):
        i1.ra = [11.]*u.deg


def test_create_nodata_frames():
    from ..builtin_frames import ICRS, FK4, FK5

    i = ICRS()
    assert len(ICRS.frame_attr_names) == 0

    f5 = FK5()
    assert f5.equinox == FK5.frame_attr_names['equinox']

    f4 = FK4()
    assert f4.equinox == FK4.frame_attr_names['equinox']
    assert f4.obstime == FK4.frame_attr_names['obstime']
