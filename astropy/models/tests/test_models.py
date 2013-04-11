# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for model evaluation.
Compare the results of some models with other programs.
"""
from __future__ import division
from .. import models
import numpy as np
from numpy.testing import utils
from ...tests.helper import pytest

class TestSComposite(object):
    """
    Test composite models evaluation in series
    """
    def setup_class(self):
        self.x, self.y = np.mgrid[:5, :5]
        self.p1= models.Poly1DModel(3)
        self.p11= models.Poly1DModel(3)
        self.p2 = models.Poly2DModel(3)
        
    def test_single_array_input(self):
        scomptr = models.SCompositeModel([self.p1, self.p11])
        sresult = scomptr(self.x)
        xx = self.p11(self.p1(self.x))
        utils.assert_almost_equal(xx, sresult)
        
    def test_labeledinput(self):
        ado = models.LabeledInput([self.x, self.y], ['x', 'y'])
        scomptr = models.SCompositeModel([self.p2, self.p1], [['x', 'y'], ['z']], [['z'], ['z']])
        sresult = scomptr(ado)
        z = self.p2(self.x, self.y)
        z1 = self.p1(z)
        utils.assert_almost_equal(z1, sresult.z)
        
    def test_multiple_arrays(self):
        scomptr = models.SCompositeModel([self.p2, self.p1], [['x', 'y'], ['z']], [['z'], ['z']])
        sresult = scomptr(self.x, self.y)
        z = self.p2(self.x, self.y)
        z1 = self.p1(z)
        utils.assert_almost_equal(z1, sresult)
        
class TestPComposite(object):
    """
    Test composite models evaluation in parallel
    """
    def setup_class(self):
        self.x, self.y = np.mgrid[:5, :5]
        self.p1= models.Poly1DModel(3)
        self.p11= models.Poly1DModel(3)
        self.p2 = models.Poly2DModel(3)
        
    def test_single_array_input(self):
        pcomptr = models.PCompositeModel([self.p1, self.p11])
        presult = pcomptr(self.x)
        delta11 = self.p11(self.x) - self.x
        delta1 = self.p1(self.x) - self.x
        xx = self.x + delta1 + delta11
        utils.assert_almost_equal(xx, presult)
        
    def test_labeledinput(self):
        ado = models.LabeledInput([self.x, self.y], ['x', 'y'])
        pcomptr=models.PCompositeModel([self.p1, self.p11], inmap=['x'], outmap=['x'])
        presult = pcomptr(ado)
        delta11 = self.p11(self.x) - self.x
        delta1 = self.p1(self.x) - self.x
        xx = self.x + delta1 + delta11
        utils.assert_almost_equal(xx, presult.x)


        