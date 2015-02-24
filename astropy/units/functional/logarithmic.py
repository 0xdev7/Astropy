# -*- coding: utf-8 -*-
from __future__ import (absolute_import, unicode_literals,
                        division, print_function)
import numpy as np

from .. import (CompositeUnit, Unit, UnitsError, dimensionless_unscaled,
                si, astrophys as ap)
from .core import FunctionalUnitBase, FunctionalQuantityBase


__all__ = ['LogUnit', 'MagUnit', 'DexUnit', 'DecibelUnit',
           'LogQuantity', 'Magnitude', 'Decibel', 'Dex',
           'STmag', 'ABmag', 'mag']


class LogUnit(FunctionalUnitBase):
    """Logarithmic unit containing a physical one

    Usually, logarithmic units are instantiated via specific subclasses
    such `MagUnit`, `dBUnit`, and `DexUnit`.

    Parameters
    ----------
    physical_unit : `~astropy.units.Unit` or `string`
        Unit that is encapsulated within the logarithmic functional unit.
        If not given, dimensionless.

    functional_unit :  `~astropy.units.Unit` or `string`
        By default, the same as the logarithmic unit set by the subclass.

    """
    # vvvv the four essential overrides of FunctionalUnitBase
    _functional_unit = ap.dex

    def from_physical(self, x):
        """Transformation from value in physical to value in logarithmic units.
        Used in equivalency"""
        return ap.dex.to(self._functional_unit, np.log10(x))

    def to_physical(self, x):
        """Transformation from value in logarithmic to value in physical units.
        Used in equivalency"""
        return 10 ** self._functional_unit.to(ap.dex, x)

    def functional_quantity(self, quantity):
        return LogQuantity(quantity, self)
    # ^^^^ the four essential overrides of FunctionalUnitBase

    # add addition and subtraction, which imply multiplication/division of
    # the underlying physical units
    def _add_and_adjust_physical_unit(self, other, sign_self, sign_other):
        """Add/subtract LogUnit to/from another unit, and adjust physical unit.

        self and other are multiplied by sign_self and sign_other, resp.

        We wish to do:   ±lu_1 + ±lu_2  -> lu_f          (lu=logarithmic unit)
                  and     pu_1^(±1) * pu_2^(±1) -> pu_f  (pu=physical unit)

        Raises UnitsError if functional units are not equivalent
        """
        # first, insist on compatible logarithmic type; note that
        # plain u.mag,u.dex,u.dB is OK, other does not have to be LogUnit
        # (this will indirectly test whether other is a unit at all)
        try:
            self._functional_unit._to(getattr(other, 'functional_unit', other))
        except AttributeError:  # if other is not a unit (_to cannot decompose)
            return NotImplemented
        except UnitsError:
            raise UnitsError("Can only add/subtract logarithmic units of"
                             "of compatible type")

        other_physical_unit = getattr(other, 'physical_unit',
                                      dimensionless_unscaled)
        physical_unit = CompositeUnit(
            1, [self._physical_unit, other_physical_unit],
            [sign_self, sign_other])

        return self._copy(physical_unit)

    def __neg__(self):
        return self._copy(self.physical_unit**(-1), -self._functional_unit)

    def __add__(self, other):
        # Only know how to add to a logarithmic unit with compatible type,
        # be it a plain one (u.mag, etc.,) or another LogUnit
        return self._add_and_adjust_physical_unit(other, +1, +1)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        return self._add_and_adjust_physical_unit(other, +1, -1)

    def __rsub__(self, other):
        # here, in normal usage other cannot be LogUnit; only equivalent one
        # would be u.mag,u.dB,u.dex.  But might as well use common routine.
        return self._add_and_adjust_physical_unit(other, -1, 1)


class MagUnit(LogUnit):
    """Logarithmic physical units expressed in magnitudes

    Parameters
    ----------
    physical_unit : `~astropy.units.Unit` or `string`
        Unit that is encapsulated within the magnitude functional unit.
        If not given, dimensionless.

    functional_unit :  `~astropy.units.Unit` or `string`
        By default, this is `~astrophys.units.mag`, but this allows one to
        use an equivalent unit such as `2 mag`.
    """
    _functional_unit = ap.mag

    def functional_quantity(self, quantity):
        return Magnitude(quantity, self)


class DexUnit(LogUnit):
    """Logarithmic physical units expressed in magnitudes

    Parameters
    ----------
    physical_unit : `~astropy.units.Unit` or `string`
        Unit that is encapsulated within the magnitude functional unit.
        If not given, dimensionless.

    functional_unit :  `~astropy.units.Unit` or `string`
        By default, this is `~astrophys.units.mag`, but this allows one to
        use an equivalent unit such as `0.5 dex`.
    """

    _functional_unit = ap.dex

    def functional_quantity(self, quantity):
        return Dex(quantity, self)


class DecibelUnit(LogUnit):
    """Logarithmic physical units expressed in dB

    Parameters
    ----------
    physical_unit : `~astropy.units.Unit` or `string`
        Unit that is encapsulated within the decibel functional unit.
        If not given, dimensionless.

    functional_unit :  `~astropy.units.Unit` or `string`
        By default, this is `~astrophys.units.mag`, but this allows one to
        use an equivalent unit such as `2 dB`.
    """

    _functional_unit = ap.dB

    def functional_quantity(self, quantity):
        return Decibel(quantity, self)


class LogQuantity(FunctionalQuantityBase):
    """A representation of a (scaled) logarithm of a number with a unit

    Parameters
    ----------
    value : number, `~astropy.units.Quantity`,
            `~astropy.units.logarithmic.LogQuantity`,
            or sequence of convertible items.
        The numerical value of the logarithmic quantity. If a number or
        a `Quantity` with a logarithmic unit, it will be converted to `unit`
        and the physical unit will be inferred from `unit`.
        If a `Quantity` with just a physical unit, it will converted to
        the logarithmic unit, after, if necessary, converting it to the
        physical unit inferred from `unit`.

    unit : functional unit, or `~astropy.units.functional.FunctionalUnit`,
            optional
        E.g., `~astropy.units.functional.mag`, `astropy.units.functional.dB`,
        `~astropy.units.functional.MagUnit`, etc.
        For a `FunctionalUnit` instance, the physical unit will be taken from
        it; for non-`FunctionalUnit` input, it will be inferred from `value`.
        By default, `unit` is set by the subclass.

    dtype : `~numpy.dtype`, optional
        The ``dtype`` of the resulting Numpy array or scalar that will
        hold the value.  If not provided, is is determined automatically
        from the input value.

    copy : bool, optional
        If `True` (default), then the value is copied.  Otherwise, a copy
        will only be made if :func:`__array__` returns a copy, if obj is a
        nested sequence, or if a copy is needed to satisfy ``dtype``.
        (The `False` option is intended mostly for internal use, to speed
        up initialization where it is known a copy has been made already.
        Use with care.)

    Examples
    --------
    Typically, use is made of a `FunctionalQuantity` subclasses, as in
        >>> import astropy.units as u
        >>> u.Magnitude(15.)
        <Magnitude 15.0 mag>
        >>> u.Magnitude(10.*u.count/u.second)
        <Magnitude -2.5 mag(ct / s)>
        >>> u.Decibel(1.*u.W, u.DecibelUnit(u.mW))
        <Decibel 30.0 dB(mW)>
    """
    # vvvv only override of FunctionalQuantity
    _FunctionalUnit = LogUnit

    # vvvv additions that work just for logarithmic units
    def __add__(self, other):
        # add units, thus multiplying physical ones; if no unit given
        # -> dimensionless_unscaled -> appropriate exception in LogUnit.__add__
        new_unit = self.unit + getattr(other, 'unit', dimensionless_unscaled)
        # add actual logarithmic values, rescaling, e.g., dB -> dex
        result = self.functional_value + getattr(other, 'functional_value',
                                                 other)
        result = result.view(self.__class__)
        result._full_unit = new_unit
        return result

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        # add units, thus multiplying physical ones; do this before overwriting
        # data (if this works, next step will succeed)
        new_unit = self.unit + getattr(other, 'unit', dimensionless_unscaled)
        # add logarithmic quantities; note: functional_value is view on array
        functional_value = self.functional_value
        functional_value += getattr(other, 'functional_value', other)
        self._full_unit = new_unit
        return self

    def __sub__(self, other):
        # subtract units, thus dividing physical ones
        new_unit = self.unit - getattr(other, 'unit', dimensionless_unscaled)
        # subtract actual logarithmic values, rescaling, e.g., dB -> dex
        result = self.functional_value - getattr(other, 'functional_value',
                                                 other)
        result = result.view(self.__class__)
        result._full_unit = new_unit
        return result

    def __rsub__(self, other):
        # subtract units, thus dividing physical ones
        new_unit = self.unit.__rsub__(
            getattr(other, 'unit', dimensionless_unscaled))
        # subtract logarithmic quantities; rescaling, e.g., dB -> dex
        result = self.functional_value.__rsub__(
            getattr(other, 'functional_value', other))
        # ensure result is in right functional unit scale
        # (with rsub, this does not have to be one's one
        result = result.to(new_unit.functional_unit).view(self.__class__)
        result._full_unit = new_unit
        return result

    def __isub__(self, other):
        # subtract units, this dividing physical ones; do this before
        # overwriting data (if this works, next step will succeed)
        new_unit = self.unit - getattr(other, 'unit', dimensionless_unscaled)
        # subtract logarithmic quantities; note: functional_value is view
        functional_value = self.functional_value
        functional_value -= getattr(other, 'functional_value', other)
        self._full_unit = new_unit
        return self

    # could add __mul__ and __div__ and try interpreting other as a power,
    # but this seems just too error-prone


class Dex(LogQuantity):
    _FunctionalUnit = DexUnit


class Decibel(LogQuantity):
    _FunctionalUnit = DecibelUnit


class Magnitude(LogQuantity):
    _FunctionalUnit = MagUnit


mag = MagUnit()

AB0 = Unit('AB', 10.**(-0.4*48.6) * 1.e-3 * si.W / si.m**2 / si.Hz,
           doc="AB magnitude zero flux density")

ST0 = Unit('ST', 10.**(-0.4*21.1) * 1.e-3 * si.W / si.m**2 / si.AA,
           doc="ST magnitude zero flux density")

STmag = MagUnit(ST0)

ABmag = MagUnit(AB0)

# inst = MagUnit(ap.count / si.second)
