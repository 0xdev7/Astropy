# -*- coding: utf-8 -*-

import pytest

from astropy.extern import six

import astropy.units as u

if not six.PY2:
    from .py3_test_quantity_annotations import *

def test_args():
    @u.QuantityInput(solarx=u.arcsec, solary=u.arcsec)
    def myfunc_args(solarx, solary):
        return solarx, solary
    
    solarx, solary = myfunc_args(1*u.arcsec, 1*u.arcsec)
    
    assert isinstance(solarx, u.Quantity)
    assert isinstance(solary, u.Quantity)
    
    assert solarx.unit == u.arcsec
    assert solary.unit == u.arcsec

def test_args_noconvert():
    @u.QuantityInput(solarx=u.arcsec, solary=u.arcsec)
    def myfunc_args(solarx, solary):
        return solarx, solary

    solarx, solary = myfunc_args(1*u.deg, 1*u.arcmin)
    
    assert isinstance(solarx, u.Quantity)
    assert isinstance(solary, u.Quantity)

    assert solarx.unit == u.deg
    assert solary.unit == u.arcmin


def test_args_nonquantity():
    @u.QuantityInput(solarx=u.arcsec)
    def myfunc_args(solarx, solary):
        return solarx, solary
    
    solarx, solary = myfunc_args(1*u.arcsec, 100)
    
    assert isinstance(solarx, u.Quantity)
    assert isinstance(solary, int)
    
    assert solarx.unit == u.arcsec

def test_arg_equivalencies():
    @u.QuantityInput(solarx=u.arcsec, solary=u.eV, equivalencies=u.mass_energy())
    def myfunc_args(solarx, solary):
        return solarx, solary
    
    solarx, solary = myfunc_args(1*u.arcsec, 100*u.gram)
    
    assert isinstance(solarx, u.Quantity)
    assert isinstance(solary, u.Quantity)
    
    assert solarx.unit == u.arcsec
    assert solary.unit == u.gram

def test_wrong_unit():
    @u.QuantityInput(solarx=u.arcsec, solary=u.deg)
    def myfunc_args(solarx, solary):
        return solarx, solary
   
    with pytest.raises(u.UnitsError) as e:
        solarx, solary = myfunc_args(1*u.arcsec, 100*u.km)
    assert str(e.value) == "Argument 'solary' to function 'myfunc_args' must be in units convertable to 'deg'."

def test_not_quantity():
    @u.QuantityInput(solarx=u.arcsec, solary=u.deg)
    def myfunc_args(solarx, solary):
        return solarx, solary
   
    with pytest.raises(TypeError) as e:
        solarx, solary = myfunc_args(1*u.arcsec, 100)
    assert str(e.value) == "Argument 'solary' to function 'myfunc_args' must be an astropy Quantity object"

def test_kwargs():
    @u.QuantityInput(solarx=u.arcsec, myk=u.deg)
    def myfunc_args(solarx, solary, myk=1*u.arcsec):
        return solarx, solary, myk
    
    solarx, solary, myk = myfunc_args(1*u.arcsec, 100, myk=100*u.deg)
    
    assert isinstance(solarx, u.Quantity)
    assert isinstance(solary, int)
    assert isinstance(myk, u.Quantity)

    assert myk.unit == u.deg

def test_unused_kwargs():
    @u.QuantityInput(solarx=u.arcsec, myk=u.deg)
    def myfunc_args(solarx, solary, myk=1*u.arcsec, myk2=1000):
        return solarx, solary, myk, myk2
    
    solarx, solary, myk, myk2 = myfunc_args(1*u.arcsec, 100, myk=100*u.deg, myk2=10)
    
    assert isinstance(solarx, u.Quantity)
    assert isinstance(solary, int)
    assert isinstance(myk, u.Quantity)
    assert isinstance(myk2, int)

    assert myk.unit == u.deg
    assert myk2 == 10

def test_kwarg_equivalencies():
    @u.QuantityInput(solarx=u.arcsec, energy=u.eV, equivalencies=u.mass_energy())
    def myfunc_args(solarx, energy=10*u.eV):
        return solarx, energy
    
    solarx, energy = myfunc_args(1*u.arcsec, 100*u.gram)
    
    assert isinstance(solarx, u.Quantity)
    assert isinstance(energy, u.Quantity)
    
    assert solarx.unit == u.arcsec
    assert energy.unit == u.gram

def test_kwarg_wrong_unit():
    @u.QuantityInput(solarx=u.arcsec, solary=u.deg)
    def myfunc_args(solarx, solary=10*u.deg):
        return solarx, solary
   
    with pytest.raises(u.UnitsError) as e:
        solarx, solary = myfunc_args(1*u.arcsec, solary=100*u.km)
    assert str(e.value) == "Argument 'solary' to function 'myfunc_args' must be in units convertable to 'deg'."

def test_kwarg_not_quantity():
    @u.QuantityInput(solarx=u.arcsec, solary=u.deg)
    def myfunc_args(solarx, solary=10*u.deg):
        return solarx, solary
   
    with pytest.raises(TypeError) as e:
        solarx, solary = myfunc_args(1*u.arcsec, solary=100)
    assert str(e.value) == "Argument 'solary' to function 'myfunc_args' must be an astropy Quantity object"
