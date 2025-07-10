import os
import sys

def get_resource_path(filename):
    """ Get the path to a bundled resource (works in dev and PyInstaller) """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)