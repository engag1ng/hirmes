"""
Functions for interacting with system after bundling.

Typical usage:
    bundled_path = get_resource_path(file_name)
"""

import os
import sys

def get_resource_path(file_name):
    """ Get the path to a bundled resource (works in dev and PyInstaller) """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, file_name) # pylint: disable=protected-access
    return os.path.join(os.path.abspath("."), file_name)
