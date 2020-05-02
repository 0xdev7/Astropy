# Licensed under a 3-clause BSD style license - see LICENSE.rst

from astropy import config as _config
from .column import Column, MaskedColumn, StringTruncateWarning, ColumnInfo

__all__ = ['BST', 'Column', 'ColumnGroups', 'ColumnInfo', 'Conf', 'FastBST',
           'FastRBT', 'JSViewer', 'MaskedColumn', 'NdarrayMixin', 'QTable', 'Row',
           'SCEngine', 'SerializedColumn', 'SortedArray', 'StringTruncateWarning',
           'Table', 'TableAttribute', 'TableColumns', 'TableFormatter',
           'TableGroups', 'TableMergeError', 'TableReplaceWarning', 'conf',
           'connect', 'hstack', 'join', 'registry', 'represent_mixins_as_columns',
           'setdiff', 'unique', 'vstack', 'dstack', 'conf', 'join_skycoord',
           'join_distance']


class Conf(_config.ConfigNamespace):  # noqa
    """
    Configuration parameters for `astropy.table`.
    """

    auto_colname = _config.ConfigItem(
        'col{0}',
        'The template that determines the name of a column if it cannot be '
        'determined. Uses new-style (format method) string formatting.',
        aliases=['astropy.table.column.auto_colname'])
    default_notebook_table_class = _config.ConfigItem(
        'table-striped table-bordered table-condensed',
        'The table class to be used in Jupyter notebooks when displaying '
        'tables (and not overridden). See <https://getbootstrap.com/css/#tables '
        'for a list of useful bootstrap classes.')
    replace_warnings = _config.ConfigItem(
        [],
        'List of conditions for issuing a warning when replacing a table '
        "column using setitem, e.g. t['a'] = value.  Allowed options are "
        "'always', 'slice', 'refcount', 'attributes'.",
        'list')
    replace_inplace = _config.ConfigItem(
        False,
        'Always use in-place update of a table column when using setitem, '
        "e.g. t['a'] = value.  This overrides the default behavior of "
        "replacing the column entirely with the new value when possible. "
        "This configuration option will be deprecated and then removed in "
        "subsequent major releases.")


conf = Conf()  # noqa

from .groups import TableGroups, ColumnGroups
from .table import (Table, QTable, TableColumns, Row, TableFormatter,
                    NdarrayMixin, TableReplaceWarning, TableAttribute)
from .operations import (join, setdiff, hstack, dstack, vstack, unique, TableMergeError,
                         join_skycoord, join_distance)
from .bst import BST, FastBST, FastRBT
from .sorted_array import SortedArray
from .soco import SCEngine
from .serialize import SerializedColumn, represent_mixins_as_columns

# Finally import the formats for the read and write method but delay building
# the documentation until all are loaded. (#5275)
from astropy.io import registry

with registry.delay_doc_updates(Table):
    # Import routines that connect readers/writers to astropy.table
    from .jsviewer import JSViewer
    import astropy.io.ascii.connect
    import astropy.io.fits.connect
    import astropy.io.misc.connect
    import astropy.io.votable.connect
    import astropy.io.misc.asdf.connect
    import astropy.io.misc.pandas.connect  # noqa
