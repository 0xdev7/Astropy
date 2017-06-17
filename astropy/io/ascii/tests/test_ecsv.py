# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
This module tests some of the methods related to the ``ECSV``
reader/writer.

Requires `pyyaml <http://pyyaml.org/>`_ to be installed.
"""
import os
import copy
import sys

import pytest
import numpy as np

from ....table import Table, Column, QTable, NdarrayMixin
from ....table.table_helpers import simple_table
from ....coordinates import SkyCoord, Latitude, Longitude, Angle, EarthLocation
from ....time import Time
from ....tests.helper import quantity_allclose

from ....extern.six.moves import StringIO
from ..ecsv import DELIMITERS
from ... import ascii
from .... import units as u

try:
    import yaml  # pylint: disable=W0611
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

DTYPES = ['bool', 'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32',
          'uint64', 'float16', 'float32', 'float64', 'float128',
          'str']
if os.name == 'nt' or sys.maxsize <= 2**32:
    DTYPES.remove('float128')

T_DTYPES = Table()

for dtype in DTYPES:
    if dtype == 'bool':
        data = np.array([False, True, False])
    elif dtype == 'str':
        data = np.array(['ab 0', 'ab, 1', 'ab2'])
    else:
        data = np.arange(3, dtype=dtype)
    c = Column(data, unit='m / s', description='descr_' + dtype,
               meta={'meta ' + dtype: 1})
    T_DTYPES[dtype] = c

T_DTYPES.meta['comments'] = ['comment1', 'comment2']

# Corresponds to simple_table()
SIMPLE_LINES = ['# %ECSV 0.9',
                '# ---',
                '# datatype:',
                '# - {name: a, datatype: int64}',
                '# - {name: b, datatype: float64}',
                '# - {name: c, datatype: string}',
                'a b c',
                '1 1.0 c',
                '2 2.0 d',
                '3 3.0 e']


@pytest.mark.skipif('not HAS_YAML')
def test_write_simple():
    """
    Write a simple table with common types.  This shows the compact version
    of serialization with one line per column.
    """
    t = simple_table()

    out = StringIO()
    t.write(out, format='ascii.ecsv')
    assert out.getvalue().splitlines() == SIMPLE_LINES

@pytest.mark.skipif('not HAS_YAML')
def test_write_full():
    """
    Write a full-featured table with common types and explicitly checkout output
    """
    t = T_DTYPES['bool', 'int64', 'float64', 'str']
    lines = ['# %ECSV 0.9',
             '# ---',
             '# datatype:',
             '# - name: bool',
             '#   unit: m / s',
             '#   datatype: bool',
             '#   description: descr_bool',
             '#   meta: {meta bool: 1}',
             '# - name: int64',
             '#   unit: m / s',
             '#   datatype: int64',
             '#   description: descr_int64',
             '#   meta: {meta int64: 1}',
             '# - name: float64',
             '#   unit: m / s',
             '#   datatype: float64',
             '#   description: descr_float64',
             '#   meta: {meta float64: 1}',
             '# - name: str',
             '#   unit: m / s',
             '#   datatype: string',
             '#   description: descr_str',
             '#   meta: {meta str: 1}',
             '# meta: !!omap',
             '# - comments: [comment1, comment2]',
             'bool int64 float64 str',
             'False 0 0.0 "ab 0"',
             'True 1 1.0 "ab, 1"',
             'False 2 2.0 ab2']

    out = StringIO()
    t.write(out, format='ascii.ecsv')
    assert out.getvalue().splitlines() == lines

@pytest.mark.skipif('not HAS_YAML')
def test_write_read_roundtrip():
    """
    Write a full-featured table with all types and see that it round-trips on
    readback.  Use both space and comma delimiters.
    """
    t = T_DTYPES
    for delimiter in DELIMITERS:
        out = StringIO()
        t.write(out, format='ascii.ecsv', delimiter=delimiter)

        t2s  = [Table.read(out.getvalue(), format='ascii.ecsv'),
                Table.read(out.getvalue(), format='ascii'),
                ascii.read(out.getvalue()),
                ascii.read(out.getvalue(), format='ecsv', guess=False),
                ascii.read(out.getvalue(), format='ecsv')]
        for t2 in t2s:
            assert t.meta == t2.meta
            for name in t.colnames:
                assert t[name].attrs_equal(t2[name])
                assert np.all(t[name] == t2[name])

@pytest.mark.skipif('not HAS_YAML')
def test_bad_delimiter():
    """
    Passing a delimiter other than space or comma gives an exception
    """
    out = StringIO()
    with pytest.raises(ValueError) as err:
        T_DTYPES.write(out, format='ascii.ecsv', delimiter='|')
    assert 'only space and comma are allowed' in str(err.value)

@pytest.mark.skipif('not HAS_YAML')
def test_bad_header_start():
    """
    Bad header without initial # %ECSV x.x
    """
    lines = copy.copy(SIMPLE_LINES)
    lines[0]  = '# %ECV 0.9'
    with pytest.raises(ascii.InconsistentTableError):
        Table.read('\n'.join(lines), format='ascii.ecsv', guess=False)

@pytest.mark.skipif('not HAS_YAML')
def test_bad_delimiter_input():
    """
    Illegal delimiter in input
    """
    lines = copy.copy(SIMPLE_LINES)
    lines.insert(2, '# delimiter: |')
    with pytest.raises(ValueError) as err:
        Table.read('\n'.join(lines), format='ascii.ecsv', guess=False)
    assert 'only space and comma are allowed' in str(err.value)

@pytest.mark.skipif('not HAS_YAML')
def test_multidim_input():
    """
    Multi-dimensional column in input
    """
    t = Table([np.arange(4).reshape(2, 2)], names=['a'])
    out = StringIO()
    with pytest.raises(ValueError) as err:
        t.write(out, format='ascii.ecsv')
    assert 'ECSV format does not support multidimensional column' in str(err.value)

@pytest.mark.skipif('not HAS_YAML')
def test_round_trip_empty_table():
    """Test fix in #5010 for issue #5009 (ECSV fails for empty type with bool type)"""
    t = Table(dtype=[bool, 'i', 'f'], names=['a', 'b', 'c'])
    out = StringIO()
    t.write(out, format='ascii.ecsv')
    t2 = Table.read(out.getvalue(), format='ascii.ecsv')
    assert t.dtype == t2.dtype
    assert len(t2) == 0


@pytest.mark.skipif('not HAS_YAML')
def test_csv_ecsv_colnames_mismatch():
    """
    Test that mismatch in column names from normal CSV header vs.
    ECSV YAML header raises the expected exception.
    """
    lines = copy.copy(SIMPLE_LINES)
    header_index = lines.index('a b c')
    lines[header_index] = 'a b d'
    with pytest.raises(ValueError) as err:
        ascii.read(lines, format='ecsv')
    assert "column names from ECSV header ['a', 'b', 'c']" in str(err)


@pytest.mark.skipif('not HAS_YAML')
def test_regression_5604():
    """
    See https://github.com/astropy/astropy/issues/5604 for more.
    """
    t = Table()
    t.meta = {"foo": 5*u.km, "foo2": u.s}
    t["bar"] = [7]*u.km

    out = StringIO()
    t.write(out, format="ascii.ecsv")

    assert '!astropy.units.Unit' in out.getvalue()
    assert '!astropy.units.Quantity' in out.getvalue()


def assert_objects_equal(obj1, obj2, attrs):
    assert obj1.__class__ is obj2.__class__

    info_attrs = ['info.name', 'info.format', 'info.unit', 'info.description']
    for attr in attrs + info_attrs:
        a1 = obj1
        a2 = obj2
        for subattr in attr.split('.'):
            try:
                a1 = getattr(a1, subattr)
                a2 = getattr(a2, subattr)
            except AttributeError:
                a1 = a1[subattr]
                a2 = a2[subattr]

        if isinstance(a1, np.ndarray) and a1.dtype.kind == 'f':
            assert quantity_allclose(a1, a2, rtol=1e-10)
        else:
            assert np.all(a1 == a2)


el = EarthLocation(x=[1, 2] * u.km, y=[3, 4] * u.km, z=[5, 6] * u.km)
sc = SkyCoord([1, 2], [3, 4], unit='deg,deg', frame='fk4',
              obstime=['J1990.5'] * 2)
scc = sc.copy()
scc.representation = 'cartesian'
tm = Time([51000.5, 51001.5], format='mjd', scale='tai', precision=5, location=el)

mixin_cols = {
    'tm': tm,
    'sc': sc,
    'scc': scc,
    'scd': SkyCoord([1, 2], [3, 4], [5, 6], unit='deg,deg,m', frame='fk4',
                    obstime=['J1990.5'] * 2),
    'q': [1, 2] * u.m,
    'lat': Latitude([1, 2] * u.deg),
    'lon': Longitude([1, 2] * u.deg),
    'ang': Angle([1, 2] * u.deg),
    'el': el,
    'nd': NdarrayMixin(el)  # not supported yet
}


@pytest.mark.skipif('not HAS_YAML')
@pytest.mark.parametrize('name_col', list(mixin_cols.items()))
@pytest.mark.parametrize('table_cls', (Table, QTable))
def test_ecsv_mixins(table_cls, name_col):
    name, col = name_col

    compare_attrs = {
        'c1': ['data'],
        'c2': ['data'],
        'tm': ['value', 'shape', 'format', 'scale', 'precision',
               'in_subfmt', 'out_subfmt', 'location'],
        'sc': ['ra', 'dec', 'representation', 'frame.name'],
        'scc': ['x', 'y', 'z', 'representation', 'frame.name'],
        'scd': ['ra', 'dec', 'distance', 'representation', 'frame.name'],
        'q': ['value', 'unit'],
        'lon': ['value', 'unit'],
        'lat': ['value', 'unit'],
        'ang': ['value', 'unit'],
        'el': ['x', 'y', 'z', 'ellipsoid'],
        'nd': ['x', 'y', 'z'],
    }

    c = [1.0, 2.0]
    t = table_cls([c, col, c], names=['c1', name, 'c2'])
    t[name].info.description = 'description'

    if not t.has_mixin_columns:
        pytest.skip('column is not a mixin (e.g. Quantity subclass in Table)')

    if isinstance(t[name], NdarrayMixin):
        pytest.xfail('NdarrayMixin not supported')

    out = StringIO()
    t.write(out, format="ascii.ecsv")
    t2 = table_cls.read(out.getvalue(), format='ascii.ecsv')

    assert t.colnames == t2.colnames

    for name in t.colnames:
        assert_objects_equal(t[name], t2[name], compare_attrs[name])

    # Special case to make sure Column type doesn't leak into class data
    if name == 'tm':
        assert t2['tm']._time.jd1.__class__ is np.ndarray
        assert t2['tm']._time.jd2.__class__ is np.ndarray
