# Licensed under a 3-clause BSD style license - see LICENSE.rst
import urllib.request
import os
from datetime import datetime, timedelta

import pytest
import numpy as np
from numpy.testing import assert_array_equal

from astropy import _erfa as erfa
from astropy.time import Time
from astropy.utils.iers import iers
from astropy.utils.data import get_pkg_data_filename
from astropy.tests.helper import catch_warnings


SYSTEM_FILE = '/usr/share/zoneinfo/leap-seconds.list'


# Test leap_seconds.list in test/data.
LEAP_SECOND_LIST = get_pkg_data_filename('data/leap-seconds.list')


def test_configuration():
    # This test just ensures things stay consistent.
    # Adjust if changes are made.
    assert iers.conf.iers_leap_second_auto_url == iers.IERS_LEAP_SECOND_URL
    assert iers.conf.ietf_leap_second_auto_url == iers.IETF_LEAP_SECOND_URL


class TestReading:
    """Basic tests that leap seconds can be read."""

    def verify_day_month_year(self, ls):
        assert np.all(ls['day'] == 1)
        assert np.all((ls['month'] == 1) | (ls['month'] == 7) |
                      (ls['year'] < 1970))
        assert np.all(ls['year'] >= 1960)
        t = Time({'year': ls['year'], 'month': ls['month'], 'day': ls['day']},
                 format='ymdhms')
        assert np.all(t == Time(ls['mjd'], format='mjd'))

    def test_read_leap_second_dat(self):
        ls = iers.LeapSeconds.from_iers_leap_seconds(
            iers.IERS_LEAP_SECOND_FILE)
        # Below, >= to take into account we might ship and updated file.
        assert ls.expires >= Time('2020-06-28')
        assert ls['mjd'][0] == 41317
        assert ls['tai_utc'][0] == 10
        assert ls['mjd'][-1] >= 57754
        assert ls['tai_utc'][-1] >= 37
        self.verify_day_month_year(ls)

    def test_open_leap_second_dat(self):
        ls = iers.LeapSeconds.from_iers_leap_seconds(
            iers.IERS_LEAP_SECOND_FILE)
        ls2 = iers.LeapSeconds.open(iers.IERS_LEAP_SECOND_FILE)
        assert np.all(ls == ls2)

    @pytest.mark.parametrize('file', (
        LEAP_SECOND_LIST,
        "file:" + urllib.request.pathname2url(LEAP_SECOND_LIST)))
    def test_read_leap_seconds_list(self, file):
        ls = iers.LeapSeconds.from_leap_seconds_list(file)
        assert ls.expires == Time('2020-06-28')
        assert ls['mjd'][0] == 41317
        assert ls['tai_utc'][0] == 10
        assert ls['mjd'][-1] == 57754
        assert ls['tai_utc'][-1] == 37
        self.verify_day_month_year(ls)

    @pytest.mark.parametrize('file', (
        LEAP_SECOND_LIST,
        "file:" + urllib.request.pathname2url(LEAP_SECOND_LIST)))
    def test_open_leap_seconds_list(self, file):
        ls = iers.LeapSeconds.from_leap_seconds_list(file)
        ls2 = iers.LeapSeconds.open(file)
        assert np.all(ls == ls2)

    @pytest.mark.skipif(not os.path.isfile(SYSTEM_FILE),
                        reason=f'system does not have {SYSTEM_FILE}')
    def test_open_system_file(self):
        ls = iers.LeapSeconds.open(SYSTEM_FILE)
        assert ls.expires > datetime.now()


def make_fake_file(expiration, tmpdir):
    """copy the built-in IERS file but set a different expiration date."""
    ls = iers.LeapSeconds.from_iers_leap_seconds()
    fake_file = str(tmpdir.join('fake_leap_seconds.dat'))
    with open(fake_file, 'w') as fh:
        fh.write('\n'.join([f'#  File expires on {expiration}']
                           + str(ls).split('\n')[2:-1]))
        return fake_file


def test_fake_file(tmpdir):
    fake_file = make_fake_file('28 June 2345', tmpdir)
    fake = iers.LeapSeconds.from_iers_leap_seconds(fake_file)
    assert fake.expires == datetime(2345, 6, 28)


class TestAutoOpenExplicitLists:
    def test_auto_open_simple(self):
        # Note: files allowed to be expired.
        with catch_warnings(iers.IERSStaleWarning):
            ls = iers.LeapSeconds.auto_open([iers.IERS_LEAP_SECOND_FILE])
        assert ls.meta['data_url'] == iers.IERS_LEAP_SECOND_FILE

    def test_auto_open_erfa(self):
        with catch_warnings(iers.IERSStaleWarning):
            ls = iers.LeapSeconds.auto_open(['erfa',
                                             iers.IERS_LEAP_SECOND_FILE])
        assert ls.meta['data_url'] in ['erfa', iers.IERS_LEAP_SECOND_FILE]

    def test_fake_future_file(self, tmpdir):
        fake_file = make_fake_file('28 June 2345', tmpdir)
        # Try as system file for auto_open, setting auto_max_age such
        # that any ERFA or system files are guaranteed to be expired,
        # while the fake file is guaranteed to be OK.
        with iers.conf.set_temp('auto_max_age', -100000):
            ls = iers.LeapSeconds.auto_open([
                'erfa', iers.IERS_LEAP_SECOND_FILE, fake_file])
            assert ls.expires == datetime(2345, 6, 28)
            assert ls.meta['data_url'] == str(fake_file)
            # And as URL
            fake_url = "file:" + urllib.request.pathname2url(fake_file)
            ls2 = iers.LeapSeconds.auto_open([
                'erfa', iers.IERS_LEAP_SECOND_FILE, fake_url])
            assert ls2.expires == datetime(2345, 6, 28)
            assert ls2.meta['data_url'] == str(fake_url)

    def test_fake_expired_file(self, tmpdir):
        fake_file1 = make_fake_file('28 June 2010', tmpdir)
        fake_file2 = make_fake_file('27 June 2012', tmpdir)
        # Ignore warnings about possibly expired built-in file.
        with catch_warnings(iers.IERSStaleWarning):
            # Between these and the built-in one, the built-in file is best.
            ls = iers.LeapSeconds.auto_open([fake_file1, fake_file2,
                                             iers.IERS_LEAP_SECOND_FILE])
        assert ls.meta['data_url'] == iers.IERS_LEAP_SECOND_FILE

        # But if we remove the built-in one, the least expired one will be
        # used.
        # used and we get a warning that it is stale.
        with catch_warnings(iers.IERSStaleWarning) as w:
            ls2 = iers.LeapSeconds.auto_open([fake_file1, fake_file2])
        assert ls2.meta['data_url'] == fake_file2
        assert ls2.expires == datetime(2012, 6, 27)
        assert len(w) == 1


@pytest.mark.remote_data
class TestRemoteURLs:
    # In these tests, the results may be cached.
    # This is fine - no need to download again.
    def test_iers_url(self):
        ls = iers.LeapSeconds.auto_open([iers.IERS_LEAP_SECOND_URL])
        assert ls.expires > datetime.now()

    def test_ietf_url(self):
        ls = iers.LeapSeconds.auto_open([iers.IETF_LEAP_SECOND_URL])
        assert ls.expires > datetime.now()


class TestDefaultAutoOpen:
    """Test auto_open with different _auto_open_files."""
    def setup(self):
        self.good_enough = (datetime.now() +
                            timedelta(179 - iers.conf.auto_max_age))
        self._auto_open_files = iers.LeapSeconds._auto_open_files.copy()

    def teardown(self):
        iers.LeapSeconds._auto_open_files = self._auto_open_files

    def remove_auto_open_files(self, *files):
        """Remove some files from the auto-opener.

        The default set is restored in teardown.
        """
        for f in files:
            iers.LeapSeconds._auto_open_files.remove(f)

    def test_erfa_found(self):
        # Set huge maximum age such that whatever ERFA has is OK.
        # Since it is checked first, it should thus be found.
        with iers.conf.set_temp('auto_max_age', 100000):
            ls = iers.LeapSeconds.open()
        assert ls.meta['data_url'] == 'erfa'

    def test_builtin_found(self):
        # Set huge maximum age such that built-in file is always OK.
        # If we remove 'erfa', it should thus be found.
        self.remove_auto_open_files('erfa')
        with iers.conf.set_temp('auto_max_age', 100000):
            ls = iers.LeapSeconds.open()
        assert ls.meta['data_url'] == iers.IERS_LEAP_SECOND_FILE

    def test_fake_future_file(self, tmpdir):
        fake_file = make_fake_file('28 June 2345', tmpdir)
        # Try as system file for auto_open, setting auto_max_age such
        # that any ERFA or system files are guaranteed to be expired.
        with iers.conf.set_temp('auto_max_age', -100000), \
                iers.conf.set_temp('system_leap_second_file', fake_file):
            ls = iers.LeapSeconds.open()
        assert ls.expires == datetime(2345, 6, 28)
        assert ls.meta['data_url'] == str(fake_file)
        # And as URL
        fake_url = "file:" + urllib.request.pathname2url(fake_file)
        with iers.conf.set_temp('auto_max_age', -100000), \
                iers.conf.set_temp('iers_leap_second_auto_url', fake_url):
            ls2 = iers.LeapSeconds.open()
        assert ls2.expires == datetime(2345, 6, 28)
        assert ls2.meta['data_url'] == str(fake_url)

    def test_fake_expired_file(self, tmpdir):
        self.remove_auto_open_files('erfa', 'iers_leap_second_auto_url',
                                    'ietf_leap_second_auto_url')
        fake_file = make_fake_file('28 June 2010', tmpdir)
        with iers.conf.set_temp('system_leap_second_file', fake_file):
            # If we try this directly, the built-in file will be found.
            ls = iers.LeapSeconds.open()
            assert ls.meta['data_url'] == iers.IERS_LEAP_SECOND_FILE

            # But if we remove the built-in one, the expired one will be
            # used and we get a warning that it is stale.
            self.remove_auto_open_files(iers.IERS_LEAP_SECOND_FILE)
            with catch_warnings(iers.IERSStaleWarning) as w:
                ls2 = iers.LeapSeconds.open()
            assert ls2.meta['data_url'] == fake_file
            assert ls2.expires == datetime(2010, 6, 28)
            assert len(w) == 1

    @pytest.mark.skipif(not os.path.isfile(SYSTEM_FILE),
                        reason=f'system does not have {SYSTEM_FILE}')
    def test_system_file_always_good_enough(self, tmpdir):
        self.remove_auto_open_files('erfa')
        with iers.conf.set_temp('system_leap_second_file', SYSTEM_FILE):
            ls = iers.LeapSeconds.open()
            assert ls.expires > self.good_enough
            assert ls.meta['data_url'] in (iers.IERS_LEAP_SECOND_FILE,
                                           SYSTEM_FILE)

            # Also check with a "built-in" file that is expired
            fake_file = make_fake_file('28 June 2017', tmpdir)
            iers.LeapSeconds._auto_open_files[0] = fake_file
            ls2 = iers.LeapSeconds.open()
            assert ls2.expires > self.good_enough
            assert ls2.meta['data_url'] == SYSTEM_FILE

    @pytest.mark.remote_data
    def test_auto_open_urls_always_good_enough(self):
        # Avoid using the erfa, built-in and system files, as they might
        # be good enough already.
        self.remove_auto_open_files('erfa', iers.IERS_LEAP_SECOND_FILE,
                                    'system_leap_second_file')
        ls = iers.LeapSeconds.open()
        assert ls.expires > self.good_enough
        assert ls.meta['data_url'].startswith('http')


class ERFALeapSecondsSafe:
    """Base class for tests that change the ERFA leap-second tables.

    It ensures the original state is restored.
    """
    def setup(self):
        # Keep current leap-second table and expiration.
        self.erfa_ls = self._erfa_ls = erfa.leap_seconds.get()
        self._expires = erfa.leap_seconds._expires

    def teardown(self):
        # Restore leap-second table and expiration.
        erfa.leap_seconds.set(self.erfa_ls)
        erfa.leap_seconds._expires = self._expires


class TestFromERFA(ERFALeapSecondsSafe):
    def test_get_erfa_ls(self):
        ls = iers.LeapSeconds.from_erfa()
        assert ls.colnames == ['year', 'month', 'tai_utc']
        assert ls.expires == erfa.leap_seconds.expires
        ls_array = np.array(ls['year', 'month', 'tai_utc'])
        assert np.all(ls_array == self.erfa_ls)

    def test_get_modified_erfa_ls(self):
        erfa.leap_seconds.set(self.erfa_ls[:-2])
        ls = iers.LeapSeconds.from_erfa()
        ls_array = np.array(ls['year', 'month', 'tai_utc'])
        assert np.all(ls_array == self.erfa_ls[:-2])

    def test_open(self):
        ls = iers.LeapSeconds.open('erfa')
        ls_array = np.array(ls['year', 'month', 'tai_utc'])
        assert np.all(ls_array == self.erfa_ls)


class TestUpdateLeapSeconds(ERFALeapSecondsSafe):
    def setup(self):
        super().setup()
        # Read default leap second table.
        self.ls = iers.LeapSeconds.from_iers_leap_seconds()
        # For tests, reset ERFA table to built-in default.
        erfa.leap_seconds.set()
        self.erfa_ls = erfa.leap_seconds.get()

    def test_built_in_up_to_date(self):
        """Leap second should match between built-in and ERFA."""
        erfa_since_1970 = self.erfa_ls[self.erfa_ls['year'] > 1970]
        assert len(self.ls) >= len(erfa_since_1970), \
            "built-in leap seconds out of date"
        assert len(self.ls) <= len(erfa_since_1970), \
            "ERFA leap seconds out of date"
        overlap = np.array(self.ls['year', 'month', 'tai_utc'])
        assert np.all(overlap == erfa_since_1970.astype(overlap.dtype))

    def test_update_with_built_in(self):
        """An update with built-in should not do anything."""
        n_update = self.ls.update_erfa_leap_seconds()
        assert n_update == 0
        new_erfa_ls = erfa.leap_seconds.get()
        assert np.all(new_erfa_ls == self.erfa_ls)

    @pytest.mark.parametrize('n_short', (1, 3))
    def test_update(self, n_short):
        """Check whether we can recover removed leap seconds."""
        erfa.leap_seconds.set(self.erfa_ls[:-n_short])
        n_update = self.ls.update_erfa_leap_seconds()
        assert n_update == n_short
        new_erfa_ls = erfa.leap_seconds.get()
        assert_array_equal(new_erfa_ls, self.erfa_ls)
        # Check that a second update does not do anything.
        n_update2 = self.ls.update_erfa_leap_seconds()
        assert n_update2 == 0
        new_erfa_ls2 = erfa.leap_seconds.get()
        assert_array_equal(new_erfa_ls2, self.erfa_ls)

    def test_update_initialize_erfa(self):
        # With pre-initialization, update does nothing.
        erfa.leap_seconds.set(self.erfa_ls[:-2])
        n_update = self.ls.update_erfa_leap_seconds(initialize_erfa=True)
        assert n_update == 0
        new_erfa_ls = erfa.leap_seconds.get()
        assert_array_equal(new_erfa_ls, self.erfa_ls)

    def test_bad_jump(self):
        erfa.leap_seconds.set(self.erfa_ls[:-2])
        bad = self.ls.copy()
        bad['tai_utc'][-1] = 5
        with pytest.raises(ValueError, match='jump'):
            bad.update_erfa_leap_seconds()
        # With an error the ERFA table should not change.
        assert_array_equal(erfa.leap_seconds.get(), self.erfa_ls[:-2])

        # Unless we initialized it beforehand.
        with pytest.raises(ValueError, match='jump'):
            bad.update_erfa_leap_seconds(initialize_erfa=True)
        assert_array_equal(erfa.leap_seconds.get(), self.erfa_ls)

        # Of course, we get no errors if we initialize only.
        erfa.leap_seconds.set(self.erfa_ls[:-2])
        n_update = bad.update_erfa_leap_seconds(initialize_erfa='only')
        assert n_update == 0
        new_erfa_ls = erfa.leap_seconds.get()
        assert_array_equal(new_erfa_ls, self.erfa_ls)

    def test_bad_day(self):
        erfa.leap_seconds.set(self.erfa_ls[:-2])
        bad = self.ls.copy()
        bad['day'][-1] = 5
        with pytest.raises(ValueError, match='not on 1st'):
            bad.update_erfa_leap_seconds()

    def test_bad_month(self):
        erfa.leap_seconds.set(self.erfa_ls[:-2])
        bad = self.ls.copy()
        bad['month'][-1] = 5
        with pytest.raises(ValueError, match='January'):
            bad.update_erfa_leap_seconds()
        assert_array_equal(erfa.leap_seconds.get(), self.erfa_ls[:-2])
