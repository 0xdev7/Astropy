import pytest
import numpy as np

import astropy.time as atm


class TestGuess():
    """Test guessing the input value format"""

    def test_guess1(self):
        times = ['1999-01-01 00:00:00.123456789', '2010-01-01 00:00:00']
        t = atm.Time(times, scale='utc')
        assert (repr(t) == "<Time object: scale='utc' format='iso' "
                "vals=['1999-01-01 00:00:00.123' '2010-01-01 00:00:00.000']>")

    def test_guess2(self):
        times = ['1999-01-01 00:00:00.123456789', '2010-01 00:00:00']
        with pytest.raises(ValueError):
            t = atm.Time(times, scale='utc')

    def test_guess3(self):
        times = ['1999:001:00:00:00.123456789', '2010:001']
        t = atm.Time(times, scale='utc')
        assert (repr(t) == "<Time object: scale='utc' format='yday' "
                "vals=['1999:001:00:00:00.123' '2010:001:00:00:00.000']>")

    def test_guess4(self):
        times = [10, 20]
        with pytest.raises(ValueError):
            t = atm.Time(times, scale='utc')
