"""
DEPRECATED: Use modules.profiles instead
=========================================
This module is kept for backwards compatibility.
All functionality has been moved to modules/profiles/.

Migration:
    # Old
    from modules.gmail.profiles import load_profile, get_team_config

    # New
    from modules.profiles import load_profile_dict as load_profile
    from modules.profiles import get_team_config_dict as get_team_config
"""

import warnings
from pathlib import Path
from typing import Dict, List, Optional, Any

# Re-export from new module
from modules.profiles import (
    load_profile_dict as _load_profile,
    get_team_config_dict as _get_team_config,
    load_profiles as _load_profiles,
    list_available,
)


def _deprecation_warning(func_name: str):
    warnings.warn(
        f"modules.gmail.profiles.{func_name}() is deprecated. "
        f"Use modules.profiles instead.",
        DeprecationWarning,
        stacklevel=3
    )


def load_profiles(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """DEPRECATED: Use modules.profiles.load_profiles()"""
    _deprecation_warning("load_profiles")
    return _load_profiles(config_path)


def load_profile(
    profile_key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """DEPRECATED: Use modules.profiles.load_profile_dict()"""
    _deprecation_warning("load_profile")
    return _load_profile(profile_key, config_path)


def get_team_config(
    team_key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """DEPRECATED: Use modules.profiles.get_team_config_dict()"""
    _deprecation_warning("get_team_config")
    return _get_team_config(team_key, config_path)


def get_profile_or_team(
    key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """DEPRECATED: Use modules.profiles.get_profile_or_team()"""
    _deprecation_warning("get_profile_or_team")
    try:
        return _load_profile(key, config_path)
    except KeyError:
        return _get_team_config(key, config_path)


def list_available_profiles(config_path: Optional[Path] = None) -> Dict[str, List[str]]:
    """DEPRECATED: Use modules.profiles.list_available()"""
    _deprecation_warning("list_available_profiles")
    return list_available(config_path)

