# version.py
"""
TenderAI Version Management
"""

__version__ = "3.0.1"
__version_info__ = (3, 0, 1)
__version_date__ = "2026-06-27"

# App metadata
__app_name__ = "TenderAI"
__app_desc__ = "Bid Optimization Platform"

def get_version():
    """Return the current version string"""
    return __version__

def get_version_info():
    """Return version info as tuple"""
    return __version_info__

def get_full_version():
    """Return full version string with date"""
    return f"v{__version__} ({__version_date__})"

def get_app_name():
    """Return application name with version"""
    return f"{__app_name__} {get_full_version()}"

def get_app_desc():
    """Return application description"""
    return __app_desc__

def get_copyright():
    """Return copyright notice"""
    return f"© 2024-2026 {__app_name__}. All rights reserved."