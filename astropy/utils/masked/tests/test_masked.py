# Licensed under a 3-clause BSD style license - see LICENSE.rst
import numpy as np
from numpy.testing import assert_array_equal

from astropy import units as u
from astropy.units import Quantity
from astropy.coordinates import Longitude
from ..core import Masked
from ....tests.helper import pytest


class ArraySetup:
    def setup_arrays(self):
        self.a = np.arange(6.).reshape(2, 3)
        self.mask_a = np.array([[True, False, False],
                                [False, True, False]])
        self.b = np.array([-3., -2., -1.])
        self.mask_b = np.array([False, True, False])
        self.c = np.array([[0.25], [0.5]])
        self.mask_c = np.array([[False], [True]])

    def setup(self):
        self.setup_arrays()


class QuantitySetup(ArraySetup):
    def setup_arrays(self):
        super().setup_arrays()
        self.a = Quantity(self.a, u.m)
        self.b = Quantity(self.b, u.cm)
        self.c = Quantity(self.c, u.s)


class LongitudeSetup(ArraySetup):
    def setup_arrays(self):
        super().setup_arrays()
        self.a = Longitude(self.a, u.deg)
        self.b = Longitude(self.b, u.deg)
        self.c = Longitude(self.c, u.deg)


class TestMaskedArrayInitialization(ArraySetup):
    def setup_arrays(self):
        self.a = np.arange(6.).reshape(2, 3)
        self.mask_a = np.array([[True, False, False],
                                [False, True, False]])

    def setup(self):
        self.setup_arrays()

    def test_simple(self):
        ma = Masked(self.a, mask=self.mask_a)
        assert isinstance(ma, np.ndarray)
        assert isinstance(ma, type(self.a))
        assert isinstance(ma, Masked)
        assert_array_equal(ma.data, self.a)
        assert_array_equal(ma.mask, self.mask_a)
        assert ma.mask is not self.mask_a
        assert np.may_share_memory(ma.mask, self.mask_a)


class TestMaskedQuantityInitialization(TestMaskedArrayInitialization):
    def setup_arrays(self):
        super().setup_arrays()
        self.a = Quantity(self.a, u.m)


class TestMaskSetting(ArraySetup):
    def test_whole_mask_setting(self):
        ma = Masked(self.a)
        assert ma.mask.shape == ma.shape
        assert not ma.mask.any()
        ma.mask = True
        assert ma.mask.shape == ma.shape
        assert ma.mask.all()
        ma.mask = [[True], [False]]
        assert ma.mask.shape == ma.shape
        assert_array_equal(ma.mask, np.array([[True] * 3, [False] * 3]))
        ma.mask = self.mask_a
        assert ma.mask.shape == ma.shape
        assert_array_equal(ma.mask, self.mask_a)
        assert ma.mask is not self.mask_a
        assert np.may_share_memory(ma.mask, self.mask_a)

    @pytest.mark.parametrize('item', ((1, 1),
                                      slice(None, 1),
                                      (),
                                      1))
    def test_part_mask_setting(self, item):
        ma = Masked(self.a)
        ma.mask[item] = True
        expected = np.zeros(ma.shape, bool)
        expected[item] = True
        assert_array_equal(ma.mask, expected)
        ma.mask[item] = False
        assert_array_equal(ma.mask, np.zeros(ma.shape, bool))
        # Mask propagation
        mask = np.zeros(self.a.shape, bool)
        ma = Masked(self.a, mask)
        ma.mask[item] = True
        assert np.may_share_memory(ma.mask, mask)
        assert_array_equal(ma.mask, mask)


# Following are tests where we trust the initializer works.


class MaskedArraySetup(ArraySetup):
    def setup(self):
        self.setup_arrays()
        self.ma = Masked(self.a, mask=self.mask_a)
        self.mb = Masked(self.b, mask=self.mask_b)
        self.mc = Masked(self.c, mask=self.mask_c)


class TestMaskedArrayCopyFilled(MaskedArraySetup):
    def test_copy(self):
        ma_copy = self.ma.copy()
        assert type(ma_copy) is type(self.ma)
        assert_array_equal(ma_copy.data, self.ma.data)
        assert_array_equal(ma_copy.mask, self.ma.mask)
        assert not np.may_share_memory(ma_copy.data, self.ma.data)
        assert not np.may_share_memory(ma_copy.mask, self.ma.mask)

    @pytest.mark.parametrize('fill_value', (0, 1))
    def test_filled(self, fill_value):
        fill_value = fill_value * getattr(self.a, 'unit', 1)
        expected = self.a.copy()
        expected[self.ma.mask] = fill_value
        result = self.ma.filled(fill_value)
        assert_array_equal(expected, result)


class TestMaskedQuantityCopyFilled(TestMaskedArrayCopyFilled, QuantitySetup):
    pass


class TestMaskedLongitudeCopyFilled(TestMaskedArrayCopyFilled, LongitudeSetup):
    pass


class TestMaskedArrayShaping(MaskedArraySetup):
    def test_reshape(self):
        ma_reshape = self.ma.reshape((6,))
        expected_data = self.a.reshape((6,))
        expected_mask = self.mask_a.reshape((6,))
        assert ma_reshape.shape == expected_data.shape
        assert_array_equal(ma_reshape.data, expected_data)
        assert_array_equal(ma_reshape.mask, expected_mask)

    def test_ravel(self):
        ma_ravel = self.ma.ravel()
        expected_data = self.a.ravel()
        expected_mask = self.mask_a.ravel()
        assert ma_ravel.shape == expected_data.shape
        assert_array_equal(ma_ravel.data, expected_data)
        assert_array_equal(ma_ravel.mask, expected_mask)

    def test_transpose(self):
        ma_transpose = self.ma.transpose()
        expected_data = self.a.transpose()
        expected_mask = self.mask_a.transpose()
        assert ma_transpose.shape == expected_data.shape
        assert_array_equal(ma_transpose.data, expected_data)
        assert_array_equal(ma_transpose.mask, expected_mask)

    def test_iter(self):
        for ma, d, m in zip(self.ma, self.a, self.mask_a):
            assert_array_equal(ma.data, d)
            assert_array_equal(ma.mask, m)


class TestMaskedArrayItems(MaskedArraySetup):
    @pytest.mark.parametrize('item', ((1, 1),
                                      slice(None, 1),
                                      (),
                                      1))
    def test_getitem(self, item):
        ma_part = self.ma[item]
        expected_data = self.a[item]
        expected_mask = self.mask_a[item]
        assert_array_equal(ma_part.data, expected_data)
        assert_array_equal(ma_part.mask, expected_mask)

    @pytest.mark.parametrize('item', ((1, 1),
                                      slice(None, 1),
                                      (),
                                      1))
    def test_setitem(self, item):
        base = self.ma.copy()
        expected_data = self.a.copy()
        expected_mask = self.mask_a.copy()
        for mask in True, False:
            value = self.ma.__class__(base[0, 0], mask)
            base[item] = value
            expected_data[item] = value.data
            expected_mask[item] = value.mask
            assert_array_equal(base.mask, expected_mask)


class TestMaskedQuantityItems(TestMaskedArrayItems, QuantitySetup):
    pass


class TestMaskedLongitudeItems(TestMaskedArrayItems, LongitudeSetup):
    pass


class MaskedUfuncTests(MaskedArraySetup):
    def test_add(self):
        mapmb = self.ma + self.mb
        expected_data = self.a + self.b
        expected_mask = (self.ma.mask | self.mb.mask)
        assert_array_equal(mapmb.data, expected_data)
        assert_array_equal(mapmb.mask, expected_mask)

    @pytest.mark.parametrize('ufunc', (np.add, np.subtract, np.divide,
                                       np.arctan2))
    def test_2op_ufunc(self, ufunc):
        ma_mb = ufunc(self.ma, self.mb)
        expected_data = ufunc(self.a, self.b)
        expected_mask = (self.ma.mask | self.mb.mask)
        # Note: assert_array_equal also checks type, i.e., that, e.g.,
        # Longitude decays into an Angle.
        assert_array_equal(ma_mb.data, expected_data)
        assert_array_equal(ma_mb.mask, expected_mask)

    @pytest.mark.parametrize('ufunc', (np.add, np.subtract))
    @pytest.mark.parametrize('axis', (0, 1))
    def test_reduce_filled_zero(self, ufunc, axis):
        # axis=None for np.add tested indirectly by test_sum below.
        reduction = getattr(ufunc, 'reduce')
        ma_reduce = reduction(self.ma, axis=axis)
        expected_data = reduction(self.a * (1 - self.ma.mask),
                                  axis=axis)
        expected_mask = np.logical_and.reduce(self.ma.mask, axis=axis)
        assert_array_equal(ma_reduce.data, expected_data)
        assert_array_equal(ma_reduce.mask, expected_mask)

    @pytest.mark.parametrize('axis', (0, 1, None))
    def test_sum(self, axis):
        ma_sum = self.ma.sum(axis)
        filled = self.ma.data * (1. - self.ma.mask)
        expected_data = filled.sum(axis)
        assert_array_equal(ma_sum.data, expected_data)
        assert not np.any(ma_sum.mask)


class TestMaskedArrayUfuncs(MaskedUfuncTests, ArraySetup):
    @pytest.mark.parametrize('axis', (0, 1, None))
    def test_reduce_filled_one(self, axis):
        ma_reduce = np.prod(self.ma, axis=axis)
        filled = self.a.copy()
        filled[self.mask_a] = 1
        expected_data = np.prod(filled, axis=axis)
        expected_mask = np.logical_and.reduce(self.ma.mask, axis=axis)
        assert_array_equal(ma_reduce.data, expected_data)
        assert_array_equal(ma_reduce.mask, expected_mask)


class TestMaskedQuantityUfuncs(MaskedUfuncTests, QuantitySetup):
    pass


class TestMaskedLongitudeUfuncs(MaskedUfuncTests, LongitudeSetup):
    pass


class TestMaskedArrayMinMax(MaskedArraySetup):
    @pytest.mark.parametrize('axis', (0, 1, None))
    def test_min(self, axis):
        ma_sum = self.ma.min(axis)
        filled = self.a.copy()
        filled[self.mask_a] = self.a.max()
        expected_data = filled.min(axis)
        assert_array_equal(ma_sum.data, expected_data)
        assert not np.any(ma_sum.mask)

    @pytest.mark.parametrize('axis', (0, 1, None))
    def test_max(self, axis):
        ma_sum = self.ma.max(axis)
        filled = self.a.copy()
        filled[self.mask_a] = self.a.min()
        expected_data = filled.max(axis)
        assert_array_equal(ma_sum.data, expected_data)
        assert not np.any(ma_sum.mask)


class TestMaskedQuantityMinMax(TestMaskedArrayMinMax, QuantitySetup):
    pass


# Note: Longtitude doesn't work, as one cannot set elements to +/-inf.
