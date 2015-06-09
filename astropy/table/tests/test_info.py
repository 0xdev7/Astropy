# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst

# TEST_UNICODE_LITERALS

import numpy as np

from ...extern import six
from ... import units as u
from ... import time
from ...utils.column_info import column_info_factory

def test_info_attributes(table_types):
    """
    Test the info() method of printing a summary of table column attributes
    """
    a = np.array([1, 2, 3], dtype='int32')
    b = np.array([1, 2, 3], dtype='float32')
    c = np.array(['a', 'c', 'e'], dtype='|S1')
    t = table_types.Table([a, b, c], names=['a', 'b', 'c'])
    masked = 'masked=True ' if t.masked else ''
    string8 = 'string8' if six.PY2 else ' bytes8'

    # Minimal output for a typical table
    out = six.moves.cStringIO()
    t.info(out=out)
    exp = ['<{0} {1}length=3>'.format(t.__class__.__name__, masked),
           'name  dtype ',
           '---- -------',
           '   a   int32',
           '   b float32',
           '   c {0}'.format(string8)]
    assert out.getvalue().splitlines() == exp

    # All output fields including a mixin column
    t['d'] = [1,2,3] * u.m
    t['d'].description = 'description'
    t['a'].format = '%02d'
    t['e'] = time.Time([1,2,3], format='cxcsec')
    out = six.moves.cStringIO()
    t.info(out=out)
    exp = ['<{0} {1}length=3>'.format(t.__class__.__name__, masked),
           'name  dtype  unit format description class',
           '---- ------- ---- ------ ----------- -----',
           '   a   int32        %02d                  ',
           '   b float32                              ',
           '   c {0}                              '.format(string8),
           '   d float64    m        description      ',
           '   e  object                          Time']
    assert out.getvalue().splitlines() == exp

def test_info_others(table_types):
    """
    Test the info() method of printing a summary of table column statistics
    """
    a = np.array([1, 2, 1, 2], dtype='int32')
    b = np.array([1, 2, 1, 2], dtype='float32')
    c = np.array(['a', 'c', 'e', 'f'], dtype='|S1')
    d = time.Time([1, 2, 1, 2], format='cxcsec')
    t = table_types.Table([a, b, c, d], names=['a', 'b', 'c', 'd'])

    # option = 'stats'
    masked = 'masked=True ' if t.masked else ''
    out = six.moves.cStringIO()
    t.info('stats', out=out)
    table_header_line = '<{0} {1}length=4>'.format(t.__class__.__name__, masked)
    exp = [table_header_line,
           'name mean std min max',
           '---- ---- --- --- ---',
           '   a  1.5 0.5   1   2',
           '   b  1.5 0.5 1.0 2.0',
           '   c   --  --  --  --',
           '   d   --  -- 1.0 2.0']
    assert out.getvalue().splitlines() == exp

    # option = ['attributes', 'stats']
    out = six.moves.cStringIO()
    t.info(['attributes', 'stats'], out=out)
    exp = [table_header_line,
           'name  dtype  class mean std min max',
           '---- ------- ----- ---- --- --- ---',
           '   a   int32        1.5 0.5   1   2',
           '   b float32        1.5 0.5 1.0 2.0',
           '   c string8         --  --  --  --',
           '   d  object  Time   --  -- 1.0 2.0']
    assert out.getvalue().splitlines() == exp

    # option = ['attributes', custom]
    custom = column_info_factory(names=['sum', 'first'],
                                 funcs=[np.sum, lambda col: col[0]])
    out = six.moves.cStringIO()
    t.info(['attributes', custom], out=out)
    exp = [table_header_line,
           'name  dtype  class sum first',
           '---- ------- ----- --- -----',
           '   a   int32         6     1',
           '   b float32       6.0   1.0',
           '   c string8        --     a',
           '   d  object  Time  --   1.0']
    assert out.getvalue().splitlines() == exp
