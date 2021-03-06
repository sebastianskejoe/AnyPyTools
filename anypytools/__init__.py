# -*- coding: utf-8 -*-
"""AnyPyTools library."""

import sys
import platform
import logging

from anypytools.abcutils import AnyPyProcess, execute_anybodycon
from anypytools.macroutils import AnyMacro
from anypytools import macro_commands


logger = logging.getLogger('abt.anypytools')
logger.addHandler(logging.NullHandler())


__all__ = [
    'datautils', 'h5py_wrapper', 'AnyPyProcess', 'AnyMacro', 'macro_commands',
    'print_versions', 'execute_anybodycon',
]

__version__ = '0.10.10'


def print_versions():
    """Print all the versions of software that AnyPyTools relies on."""
    import numpy as np
    import scipy as sp
    print("-=" * 38)
    print("AnyPyTools version: %s" % __version__)
    print("NumPy version: %s" % np.__version__)
    print("SciPy version: %s" % sp.__version__)
    print("Python version: %s" % sys.version)
    (sysname, nodename, release, version, machine, processor) = \
        platform.uname()
    print("Platform: %s-%s-%s (%s)" % (sysname, release, machine, version))
    if sysname == "Linux":
        print("Linux dist: %s" % " ".join(platform.linux_distribution()[:-1]))
    if not processor:
        processor = "not recognized"
    print("Processor: %s" % processor)
    print("Byte-ordering: %s" % sys.byteorder)
    print("-=" * 38)
