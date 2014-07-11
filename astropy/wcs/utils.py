# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np


def add_stokes_axis_to_wcs(wcs, add_before_ind):
    """
    Add a new Stokes axis that is uncorrelated with any other axes.

    Parameters
    ----------
    wcs : `~astropy.wcs.WCS`
        The WCS to add to
    add_before_ind : int
        Index of the WCS to insert the new Stokes axis in front of.
        To add at the end, do add_before_ind = wcs.wcs.naxis
        The beginning is at position 0.

    Returns
    -------
    A new `~astropy.wcs.WCS` instance with an additional axis
    """

    inds = [i + 1 for i in range(wcs.wcs.naxis)]
    inds.insert(add_before_ind, 0)
    newwcs = wcs.sub(inds)
    newwcs.wcs.ctype[add_before_ind] = 'STOKES'
    newwcs.wcs.cname[add_before_ind] = 'STOKES'
    return newwcs


def wcs_to_celestial_frame(wcs):

    from ..coordinates import FK4, FK4NoETerms, FK5, ICRS, Galactic
    from ..time import Time

    radesys = wcs.wcs.radesys
    if np.isnan(wcs.wcs.equinox):
        equinox = None
    else:
        equinox = wcs.wcs.equinox

    xcoord = wcs.wcs.ctype[0][:4]
    ycoord = wcs.wcs.ctype[1][:4]

    # Apply logic from FITS standard
    if radesys == b'' and xcoord == b'RA--' and ycoord == b'DEC-':
        if equinox is None:
            radesys = "ICRS"
        elif equinox < 1984.:
            radesys = "FK4"
        else:
            radesys = "FK5"

    if radesys == b'FK4':
        if equinox is not None:
            equinox = Time(equinox, format='byear')
        frame = FK4(equinox=equinox)
    elif radesys == b'FK4-NO-E':
        if equinox is not None:
            equinox = Time(equinox, format='byear')
        frame = FK4NoETerms(equinox=equinox)
    elif radesys == b'FK5':
        if equinox is not None:
            equinox = Time(equinox, format='jyear')
        frame = FK5(equinox=equinox)
    elif radesys == b'ICRS':
        frame = ICRS()
    else:
        if xcoord == b'GLON' and ycoord == b'GLAT':
            if equinox is not None:
                equinox = Time(equinox, format='jyear')
            frame = Galactic(equinox=equinox)
        else:
            print(radesys, equinox, xcoord, ycoord)
            raise ValueError("Could not determine celestial frame for RADESYS={radesys}, CTYPE1={ctype1}, CTYPE2={ctype2}, EQUINOX={equinox}".format(radesys=wcs.wcs.radesys, ctype1=wcs.wcs.ctype[0], ctype2=wcs.wcs.ctype[1], equinox=wcs.wcs.equinox))

    return frame
