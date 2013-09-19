# Licensed under a 3-clause BSD style license - see LICENSE.rst
import numpy as np

from ...tests.helper import pytest

from ..kernels import Gaussian2DKernel, Box2DKernel, Tophat2DKernel
from ..convolve import convolve, convolve_fft

from numpy.testing import assert_array_almost_equal_nulp, assert_almost_equal

import itertools

SHAPES_ODD = [[15, 15], [31, 31], ]
SHAPES_EVEN = [[8, 8], [16, 16], [32, 32]]
WIDTHS = [2, 3, 4, 5]

KERNELS = []

for shape in SHAPES_ODD:
    for width in WIDTHS:

        KERNELS.append(Gaussian2DKernel(width,
                                        x_size=shape[0],
                                        y_size=shape[1],
                                        mode='oversample',
                                        factor=10))

        KERNELS.append(Box2DKernel(width,
                                   x_size=shape[0],
                                   y_size=shape[1],
                                   mode='oversample',
                                   factor=10))

        KERNELS.append(Tophat2DKernel(width,
                                      x_size=shape[0],
                                      y_size=shape[1],
                                      mode='oversample',
                                      factor=10))



class Test2DConvolutions(object):

    @pytest.mark.parametrize('kernel', KERNELS)
    def test_centered_makekernel(self, kernel):
        """
        Test smoothing of an image with a single positive pixel
        """

        shape = kernel.array.shape

        x = np.zeros(shape)
        xslice = [slice(sh // 2, sh // 2 + 1) for sh in shape]
        x[xslice] = 1.0

        c2 = convolve_fft(x, kernel, boundary='fill')
        c1 = convolve(x, kernel, boundary='fill')

        assert_almost_equal(c1, c2, decimal=12)

    @pytest.mark.parametrize('kernel', KERNELS)
    def test_random_makekernel(self, kernel):
        """
        Test smoothing of an image made of random noise
        """

        shape = kernel.array.shape

        x = np.random.randn(*shape)

        c2 = convolve_fft(x, kernel, boundary='fill')
        c1 = convolve(x, kernel, boundary='fill')

        # not clear why, but these differ by a couple ulps...
        assert_almost_equal(c1, c2, decimal=12)

    @pytest.mark.parametrize(('shape', 'width'), list(itertools.product(SHAPES_ODD, WIDTHS)))
    def test_uniform_smallkernel(self, shape, width):
        """
        Test smoothing of an image with a single positive pixel

        Instead of using make_kernel, uses a simple, small kernel
        """

        if width % 2 == 0:
            # convolve does not accept odd-shape kernels
            return

        kernel = np.ones([width, width])

        x = np.zeros(shape)
        xslice = [slice(sh // 2, sh // 2 + 1) for sh in shape]
        x[xslice] = 1.0

        c2 = convolve_fft(x, kernel, boundary='fill')
        c1 = convolve(x, kernel, boundary='fill')

        assert_almost_equal(c1, c2, decimal=12)

    @pytest.mark.parametrize(('shape', 'width'), list(itertools.product(SHAPES_ODD, [1, 3, 5])))
    def test_smallkernel_vs_makekernel(self, shape, width):
        """
        Test smoothing of an image with a single positive pixel

        Compares a small kernel to something produced by makekernel
        """

        kernel1 = np.ones([width, width]) / np.float(width) ** 2
        kernel2 = Box2DKernel(width, x_size=shape[0], y_size=shape[1],
                              mode='oversample', factor=10)

        x = np.zeros(shape)
        xslice = [slice(sh // 2, sh // 2 + 1) for sh in shape]
        x[xslice] = 1.0

        c2 = convolve_fft(x, kernel2, boundary='fill')
        c1 = convolve_fft(x, kernel1, boundary='fill')

        assert_almost_equal(c1, c2, decimal=12)

        c2 = convolve(x, kernel2, boundary='fill')
        c1 = convolve(x, kernel1, boundary='fill')

        assert_almost_equal(c1, c2, decimal=12)
