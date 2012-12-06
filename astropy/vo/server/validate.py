# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Validate VO Services.

This could be used by VO service providers to validate
their services.

.. note::

    This is not meant to be used by a typical AstroPy user.

*CONFIGURABLE PROPERTIES*

These properties are set via Astropy configuration system:

    * `astropy.vo.server.cs_mstr_list`
    * `astropy.vo.server.noncrit_warnings`
    * Also depends on properties in `astropy.vo.client`

*DEFAULT CONE SEARCH SERVICES*

Currently, the default Cone Search services used are a
subset of those found in `STScI VAO registry
<http://vao.stsci.edu/directory/NVORegInt.asmx?op=VOTCapabilityPredOpt>`_.
They are hand-picked to represent commonly used catalogs below:

    * 2MASS All-Sky
    * HST Guide Star Catalog
    * SDSS Data Release 7
    * SDSS-III Data Release 8
    * USNO A1
    * USNO A2
    * USNO B1

From this subset, the ones that pass daily validation
are used by `astropy.vo.client.conesearch` by default.

If you are a Cone Search service provider and would like
to include your service in this list, please contact the
AstroPy Team.

Examples
--------
Validate default Cone Search sites with multiprocessing
and write results in the current directory:

>>> from astropy.vo.server import validate
>>> validate.check_conesearch_sites()

Change `astropy.vo.server.cs_mstr_list` to obtain
the master list directly from STScI VAO registry:

>>> validate.CS_MSTR_LIST.set(validate._VAO_QUERY)

From the master list above, select Cone Search services
hosted by 'stsci.edu':

>>> import numpy as np
>>> from astropy.io.votable import parse_single_table
>>> from astropy.utils.data import get_readable_fileobj
>>> with get_readable_fileobj(validate.CS_MSTR_LIST()) as fd:
...     tab_all = parse_single_table(fd, pedantic=False)
>>> arr = tab_all.array.data[np.where(
...     (tab_all.array['capabilityClass'] == 'ConeSearch') &
...     (np.char.count(tab_all.array['accessURL'].tolist(), 'stsci.edu') > 0))]
>>> urls = arr['accessURL'].tolist()

Validate only the URLs found above without verbose
outputs or multiprocessing, and write results in
'subset' sub-directory:

>>> validate.check_conesearch_sites(
...     destdir='./subset', verbose=False, multiproc=False, url_list=urls)

Change `astropy.vo.server.cs_mstr_list` back to default:

>>> validate.CS_MSTR_LIST.set(validate.CS_MSTR_LIST.defaultvalue)

Add 'W24' from `astropy.io.votable.exceptions` to the list of
ignored warnings and re-run validation. This is *not*
recommended unless you know exactly what you are doing:

>>> validate.NONCRIT_WARNINGS.set(validate.NONCRIT_WARNINGS() + ['W24'])
>>> validate.check_conesearch_sites()

"""
from __future__ import print_function, division

# STDLIB
from collections import defaultdict
from copy import deepcopy
import json
import os
import time
import warnings

# THIRD PARTY
import numpy as np

# LOCAL
from ..client import vos_catalog
from ...config.configuration import ConfigurationItem
from ...io import votable
from ...io.votable.exceptions import E19
from ...io.votable.validator import html, result
from ...logger import log
from ...utils.data import get_readable_fileobj
from ...utils.misc import NumpyScalarOrSetEncoder


__all__ = ['check_conesearch_sites']

CS_MSTR_LIST = ConfigurationItem(
    'cs_mstr_list', vos_catalog.BASEURL() + 'conesearch_sites.xml',
    'Cone Search services master list for validation.')

NONCRIT_WARNINGS = ConfigurationItem(
    'noncrit_warnings',
    ['W03', 'W06', 'W07', 'W09', 'W10', 'W15', 'W17', 'W20', 'W21', 'W22',
     'W27', 'W28', 'W29', 'W41', 'W42', 'W48', 'W50'],
    'VO Table warning codes that are considered non-critical',
    'list')

_OUT_ROOT = None  # Set by `check_conesearch_sites`

# This obtains a master list of conesearch sites
_VAO_QUERY = 'http://vao.stsci.edu/directory/NVORegInt.asmx/' \
             'VOTCapabilityPredOpt?predicate=1%3D1&' \
             'capability=conesearch&VOTStyleOption=2'


def check_conesearch_sites(destdir=os.curdir, verbose=True, multiproc=True,
                           url_list=None):
    """
    Validate Cone Search Services.

    A master list of all available Cone Search sites is
    obtained from `astropy.vo.server.cs_mstr_list`, which
    is a URL query to an external VAO service or the resultant
    XML file.

    These sites are validated using `astropy.io.votable.validator`
    and separated into four groups below, each is stored as a JSON
    database in `destdir`. Existing files with same names will be
    deleted to avoid confusion:

        #. *conesearch_good.json*
               Passed validation without critical warnings and
               exceptions. This database in
               `astropy.vo.client.vos_baseurl` is the one used
               by `astropy.vo.client.conesearch` by default.
        #. *conesearch_warn.json*
               Has critical warnings but no exceptions. Users
               can manually set `astropy.vo.client.conesearch`
               to use this at their own risk.
        #. *conesearch_exception.json*
               Has some exceptions. *Never* use this.
               For informational purpose only.
        #. *conesearch_error.json*
               Has network connection error. *Never* use this.
               For informational purpose only.

    HTML pages summarizing the validation results are generated by
    `astropy.io.votable.validator` and stored in 'results'
    sub-directory, which also contains downloaded XML files from
    individual cone search queries.

    *WARNINGS AND EXCEPTIONS*

    A subset of `astropy.io.votable.exceptions` that is considered
    non-critical is defined by `astropy.vo.server.noncrit_warnings`
    configurable property. This means validation will ignore them
    (but `astropy.io.votable.table.pedantic` still needs to be set
    to `False` if user wants to use results from sites with these
    warnings). Despite listed as non-critical, user is responsible
    to check whether the results are reliable; They should not be
    used blindly.

    User can also modify the configurable property to include or
    exclude any warnings or exceptions, as desired, although adding
    exceptions is not recommended.

    *BUILDING THE DATABASE*

    For user-friendly catalog listing, title will be the catalog key.
    To avoid repeating the same query, access URL should be unique.
    In STScI VAO registry, a title can have multiple access URLs,
    and vice versa. In addition, the same title and access URL can
    also repeat under different descriptions.

    In the case of (title, url 1) and (title, url 2), they will appear
    as two different entries with title renamed to 'title N' where N
    is a sequence number. If the title does not repeat in the entire
    database, only 'title 1' exists.

    In the case of (title 1, url) and (title 2, url), database will
    use (title 1, url) and ignore (title 2, url).

    If the same (title, url) has multiple entries, database will use
    the first match and ignore the rest.

    A new field named 'duplicatesIgnored' is added to each catalog in
    the database to count ignored duplicate entries. New fields named
    'validate_xxx' are added from attributes of
    `astropy.io.votable.validate.result.Result`, where 'xxx' is the
    original attribute name.

    .. note::

        All cone search queries are done using RA, DEC, and SR
        given by `testQuery` in the registry and maximum verbosity.
        No validation is done for erroneous and meta-data queries.

        Until STScI VAO registry formally provides `testQuery`
        parameters, they are extracted from
        `astropy.vo.server.validate._TESTQUERYFILE`.

    Parameters
    ----------
    destdir : string
        Directory to store output files. Will be created if does
        not exist.

    verbose : bool
        Print extra info to log.

    multiproc : bool
        Enable multiprocessing.

    url_list : list of string
        Only check these access URLs from
        `astropy.vo.server.cs_mstr_list` and ignore the others,
        which will not appear in output files.
        If `None`, check everything.

    Raises
    ------
    AssertionError
        Parameter failed assertion test.

    timeout
        URL request timed out.

    """
    global _OUT_ROOT

    assert (not os.path.exists(destdir) and len(destdir) > 0) or \
        (os.path.exists(destdir) and os.path.isdir(destdir)), \
        'Invalid destination directory'

    if url_list is not None:
        from collections import Iterable
        assert isinstance(url_list, Iterable)
        for cur_url in url_list:
            assert isinstance(cur_url, basestring)
        url_list = np.char.replace(url_list, '&amp;', '&')

    if not os.path.exists(destdir):
        os.mkdir(destdir)

    # Output dir created by votable.validator
    _OUT_ROOT = os.path.join(destdir, 'results')

    # Output files
    db_file = {}
    db_file['good'] = os.path.join(destdir, 'conesearch_good.json')
    db_file['warn'] = os.path.join(destdir, 'conesearch_warn.json')
    db_file['excp'] = os.path.join(destdir, 'conesearch_exception.json')
    db_file['nerr'] = os.path.join(destdir, 'conesearch_error.json')

    # JSON dictionaries for output files
    js_template = {'__version__': 1, 'catalogs': {}}
    js_mstr = deepcopy(js_template)
    js_tree = {}
    for key in db_file:
        js_tree[key] = deepcopy(js_template)

        # Delete existing files, if any, to be on the safe side.
        # Else can cause confusion if program exited prior to
        # new files being written but old files are still there.
        if os.path.exists(db_file[key]):
            os.remove(db_file[key])
            if verbose:
                log.info('Existing file {} deleted'.format(db_file[key]))

    # Get all Cone Search sites
    with get_readable_fileobj(CS_MSTR_LIST()) as fd:
        tab_all = votable.parse_single_table(fd, pedantic=False)
    arr_cone = tab_all.array.data[np.where(
        tab_all.array['capabilityClass'] == 'ConeSearch')]

    assert arr_cone.size > 0, \
        'astropy.vo.server.cs_mstr_list yields no valid result'

    # Fix URL syntax or queries will fail
    fixed_urls = np.char.replace(arr_cone['accessURL'].tolist(), '&amp;', '&')

    # Re-structure dictionary for JSON file

    col_names = arr_cone.dtype.names
    uniq_urls = set(fixed_urls)
    uniq_rows = len(uniq_urls)
    check_sum = 0
    title_counter = defaultdict(int)
    key_lookup_by_url = {}

    for cur_url in uniq_urls:
        if url_list is not None and cur_url not in url_list:
            if verbose:
                log.info('Skipping {}'.format(cur_url))
            continue

        i_same_url = np.where(fixed_urls == cur_url)
        i = i_same_url[0][0]

        num_match = len(i_same_url[0])
        check_sum += num_match
        row_d = {'duplicatesIgnored': num_match - 1}

        cur_title = arr_cone[i]['title']
        title_counter[cur_title] += 1
        cat_key = '{} {}'.format(cur_title, title_counter[cur_title])

        for col in col_names:
            if col == 'accessURL':
                row_d['url'] = fixed_urls[i]
            else:
                row_d[col] = arr_cone[i][col]

        # Use testQuery to return non-empty VO table with max verbosity
        cs_pars_arr = [
            '='.join([key, val]) for key, val in
            _TESTQUERY[cur_url].iteritems()] + ['VERB=3']
        conesearch_pars = '&'.join(cs_pars_arr)

        js_mstr['catalogs'][cat_key] = row_d
        key_lookup_by_url[cur_url + conesearch_pars] = cat_key

    if url_list is None:
        assert check_sum == arr_cone.size, 'Database checksum error'
        assert len(js_mstr['catalogs']) == uniq_rows, \
            'Number of database entries do not match unique access URLs'

    # Validate URLs

    all_urls = key_lookup_by_url.keys()
    t_beg = time.time()

    if multiproc:
        import multiprocessing
        mp_list = []
        pool = multiprocessing.Pool()
        mp_proc = pool.map_async(_do_validation, all_urls,
                                 callback=mp_list.append)
        mp_proc.wait()
        assert len(mp_list) > 0, \
            'Multiprocessing pool callback returned empty list'
        mp_list = mp_list[0]

    else:
        mp_list = [_do_validation(cur_url) for cur_url in all_urls]

    t_end = time.time()

    if verbose:
        log.info('Validation of {} sites took {:.3f} s'.format(uniq_rows,
                                                           t_end - t_beg))

    # Categorize validation results
    for r in mp_list:
        db_key = r['out_db_name']
        cat_key = key_lookup_by_url[r.url]
        js_tree[db_key]['catalogs'][cat_key] = js_mstr['catalogs'][cat_key]
        _copy_r_to_db(r, js_tree[db_key]['catalogs'][cat_key])

    # Write to HTML

    html_subsets = result.get_result_subsets(mp_list, _OUT_ROOT)
    html.write_index(html_subsets, all_urls, _OUT_ROOT)

    if multiproc:
        html_subindex_args = [(html_subset, uniq_rows)
                              for html_subset in html_subsets]
        pool = multiprocessing.Pool()
        mp_proc = pool.map_async(_html_subindex, html_subindex_args)
        mp_proc.wait()

    else:
        for html_subset in html_subsets:
            _html_subindex((html_subset, uniq_rows))

    # Write to JSON
    n = {}
    for key in db_file:
        n[key] = len(js_tree[key]['catalogs'])
        if verbose:
            log.info('{}: {} catalogs'.format(key, n[key]))
        with open(db_file[key], 'w') as f_json:
            f_json.write(json.dumps(js_tree[key], cls=NumpyScalarOrSetEncoder,
                                    sort_keys=True, indent=4))

    if n['good'] == 0:
        log.warn('No good sites available for Cone Search.')


def _do_validation(url):
    """Validation for multiprocessing support."""
    votable.table.reset_vo_warnings()

    r = result.Result(url, root=_OUT_ROOT)
    r.validate_vo()

    _categorize_result(r)

    # This was already checked above.
    # Calling this again to get VOTableFile object to catch
    # well-formed error responses in downloaded XML.
    #
    # 'incorrect' is also added in case user wants to use
    # 'conesearch_warn.json' anyway.
    #
    # If using cached data, it will not detect network error
    # like the first run, but will raise exception.
    #
    # When SR is not 0, VOSError is raised for empty table.
    #
    if r['expected'] in ('good', 'incorrect') and r['nexceptions'] == 0:
        nexceptions = 0
        nwarnings = 0
        lines = []

        with warnings.catch_warnings(record=True) as warning_lines:
            try:
                tab = vos_catalog.vo_tab_parse(votable.table.parse(
                    r.get_vo_xml_path(), pedantic=False), r.url, {})
            except (E19, IndexError, vos_catalog.VOSError) as e:
                lines.append(str(e))
                nexceptions += 1
        lines = [str(x.message) for x in warning_lines] + lines

        warning_types = set()
        for line in lines:
            w = votable.exceptions.parse_vowarning(line)
            if w['is_warning']:
                nwarnings += 1
            if w['is_exception']:
                nexceptions += 1
            warning_types.add(w['warning'])

        r['nwarnings'] += nwarnings
        r['nexceptions'] += nexceptions
        r['warnings'] += lines
        r['warning_types'] = r['warning_types'].union(warning_types)

        _categorize_result(r)

    html.write_result(r)
    return r


def _categorize_result(r):
    """
    Set success codes.

    Parameters
    ----------
    r : `astropy.io.votable.validator.result.Result` object

    """
    if 'network_error' in r and r['network_error'] is not None:
        r['out_db_name'] = 'nerr'
        r['expected'] = 'broken'
    elif (r['nexceptions'] == 0 and r['nwarnings'] == 0) or \
            r['warning_types'].issubset(NONCRIT_WARNINGS()):
        r['out_db_name'] = 'good'
        r['expected'] = 'good'
    elif r['nexceptions'] > 0:
        r['out_db_name'] = 'excp'
        r['expected'] = 'incorrect'
    elif r['nwarnings'] > 0:
        r['out_db_name'] = 'warn'
        r['expected'] = 'incorrect'
    else:  # pragma: no cover
        raise vos_catalog.VOSError(
            'Unhandled validation result attributes: {}'.format(r._attributes))


def _html_subindex(args):
    """HTML writer for multiprocessing support."""
    subset, total = args
    html.write_index_table(_OUT_ROOT, *subset, total=total)


def _copy_r_to_db(r, db):
    """
    Copy validation result attributes to given JSON database entry.

    Parameters
    ----------
    r : `astropy.io.votable.validate.result.Result` object

    db : dict

    """
    for key, val in r._attributes.iteritems():
        new_key = '_'.join(['validate', key])
        db[new_key] = val


#-------------------------------------------------------------#
# Temporary solution until _VAO_QUERY includes testQuery tags #
#-------------------------------------------------------------#

_TESTQUERYFILE = vos_catalog.BASEURL() + 'conesearch_testquery.xml'


def _parse_testquery():
    """Parse testQuery pars into dict."""
    from collections import OrderedDict
    from xml.dom.minidom import parse

    tqp = OrderedDict({'testQuery_x002F_ra': 'RA',
                       'testQuery_x002F_dec': 'DEC',
                       'testQuery_x002F_sr': 'SR'})
    d = {}

    with get_readable_fileobj(_TESTQUERYFILE) as fd:
        dom = parse(fd)

    for tab in dom.getElementsByTagName('Table'):
        url = tab.getElementsByTagName('accessURL')[0].firstChild.nodeValue
        url = url.replace('&amp;', '&')
        d[url] = OrderedDict()
        for key, val in tqp.iteritems():
            d[url][val] = tab.getElementsByTagName(key)[0].firstChild.nodeValue

    return d


_TESTQUERY = _parse_testquery()
