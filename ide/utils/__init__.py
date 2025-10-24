"""
Utility modules
"""

import sys
import os


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    
    When packaged with PyInstaller, files are extracted to a temp folder.
    This function returns the correct path in both cases.
    
    Args:
        relative_path: Path relative to the application root
        
    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running as script, use current directory
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    return os.path.join(base_path, relative_path)
