# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Functions to do XML schema and DTD validation.  At the moment, this
makes a subprocess call to xmllint.  This could use a Python-based
library at some point in the future, if something appropriate could be
found.
"""

import os


def validate_schema(filename, schema_file):
    """
    Validates an XML file against a schema or DTD.

    Parameters
    ----------
    filename : str
        The path to the XML file to validate

    schema : str
        The path to the XML schema or DTD

    Returns
    -------
    returncode, stdout, stderr : int, str, str
        Returns the returncode from xmllint and the stdout and stderr
        as strings
    """
    import subprocess

    base, ext = os.path.splitext(schema_file)
    if ext == '.xsd':
        schema_part = '--schema ' + schema_file
    elif ext == '.dtd':
        schema_part = '--dtdvalid ' + schema_file
    else:
        raise TypeError("schema_file must be a path to an XML Schema or DTD")

    p = subprocess.Popen(
        "xmllint --noout --nonet %s %s" % (schema_part, filename),
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if p.returncode == 127:
        raise OSError(
            "xmllint not found, so can not validate schema")

    return p.returncode, stdout, stderr
