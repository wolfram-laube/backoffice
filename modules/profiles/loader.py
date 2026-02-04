"""
Profile Loader
==============
Loads profiles and teams from YAML configuration.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import yaml

from .models import Profile, Team


# Default config location
DEFAULT_CONFIG = Path(__file__).parent / "config.yaml"

# Cache for loaded config
_config_cache: Dict[str, Any] = {}


def _load_yaml(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and cache YAML config."""
    path = config_path or DEFAULT_CONFIG
    path_str = str(path)
    
    if path_str not in _config_cache:
        if not path.exists():
            raise FileNotFoundError(f"Profile config not found: {path}")
        
        with open(path) as f:
            _config_cache[path_str] = yaml.safe_load(f)
    
    return _config_cache[path_str]


def clear_cache():
    """Clear config cache (useful for testing)."""
    _config_cache.clear()


def load_profiles(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load full config (legacy compatibility).
    
    Returns:
        Full config dict with 'profiles', 'teams', 'defaults'
    """
    return _load_yaml(config_path)


def load_profile(
    profile_key: str,
    config_path: Optional[Path] = None
) -> Profile:
    """
    Load a single profile by key.
    
    Args:
        profile_key: Profile identifier (e.g., 'wolfram', 'ian')
        config_path: Path to config.yaml
        
    Returns:
        Profile object
    """
    config = _load_yaml(config_path)
    profiles_data = config.get("profiles", {})
    
    if profile_key not in profiles_data:
        available = list(profiles_data.keys())
        raise KeyError(f"Profile '{profile_key}' not found. Available: {available}")
    
    return Profile.from_dict(profile_key, profiles_data[profile_key])


def load_all_profiles(config_path: Optional[Path] = None) -> Dict[str, Profile]:
    """
    Load all profiles as Profile objects.
    
    Returns:
        Dict mapping profile keys to Profile objects
    """
    config = _load_yaml(config_path)
    profiles_data = config.get("profiles", {})
    
    return {
        key: Profile.from_dict(key, data)
        for key, data in profiles_data.items()
    }


def get_team_config(
    team_key: str,
    config_path: Optional[Path] = None
) -> Team:
    """
    Load team configuration.
    
    Args:
        team_key: Team identifier (e.g., 'wolfram_ian', 'all_three')
        config_path: Path to config.yaml
        
    Returns:
        Team object with resolved member profiles
    """
    config = _load_yaml(config_path)
    teams_data = config.get("teams", {})
    
    if team_key not in teams_data:
        available = list(teams_data.keys())
        raise KeyError(f"Team '{team_key}' not found. Available: {available}")
    
    team = Team.from_dict(team_key, teams_data[team_key])
    
    # Resolve member profiles
    profiles = load_all_profiles(config_path)
    team.member_profiles = [
        profiles[m] for m in team.members if m in profiles
    ]
    
    return team


def load_all_teams(config_path: Optional[Path] = None) -> Dict[str, Team]:
    """
    Load all teams with resolved member profiles.
    
    Returns:
        Dict mapping team keys to Team objects
    """
    config = _load_yaml(config_path)
    teams_data = config.get("teams", {})
    profiles = load_all_profiles(config_path)
    
    teams = {}
    for key, data in teams_data.items():
        team = Team.from_dict(key, data)
        team.member_profiles = [
            profiles[m] for m in team.members if m in profiles
        ]
        teams[key] = team
    
    return teams


def get_profile_or_team(
    key: str,
    config_path: Optional[Path] = None
) -> Union[Profile, Team]:
    """
    Load profile or team by key.
    Tries profiles first, then teams.
    
    Args:
        key: Profile or team key
        
    Returns:
        Profile or Team object
    """
    config = _load_yaml(config_path)
    
    if key in config.get("profiles", {}):
        return load_profile(key, config_path)
    elif key in config.get("teams", {}):
        return get_team_config(key, config_path)
    else:
        all_keys = (
            list(config.get("profiles", {}).keys()) +
            list(config.get("teams", {}).keys())
        )
        raise KeyError(f"'{key}' not found. Available: {all_keys}")


def list_available(config_path: Optional[Path] = None) -> Dict[str, List[str]]:
    """
    List all available profiles and teams.
    
    Returns:
        Dict with 'profiles' and 'teams' lists
    """
    config = _load_yaml(config_path)
    return {
        "profiles": list(config.get("profiles", {}).keys()),
        "teams": list(config.get("teams", {}).keys()),
    }


# =============================================================================
# Legacy API (for backwards compatibility with gmail/profiles.py)
# =============================================================================

def load_profile_dict(
    profile_key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Load a single profile as dict (legacy).
    
    Returns:
        Profile dict with name, email, rate, attachments, etc.
    """
    config = _load_yaml(config_path)
    profiles = config.get("profiles", {})
    
    if profile_key not in profiles:
        available = list(profiles.keys())
        raise KeyError(f"Profile '{profile_key}' not found. Available: {available}")
    
    profile = profiles[profile_key].copy()
    profile["key"] = profile_key
    
    # Merge defaults
    defaults = config.get("defaults", {})
    for key, value in defaults.items():
        if key not in profile:
            profile[key] = value
    
    # Flatten rate for legacy compatibility
    if isinstance(profile.get("rate"), dict):
        profile["rate"] = str(profile["rate"].get("preferred", 105))
    
    # Flatten attachments for legacy compatibility
    if isinstance(profile.get("attachments"), dict):
        profile["attachments"] = list(profile["attachments"].values())
    
    return profile


def get_team_config_dict(
    team_key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Load team configuration as dict (legacy).
    
    Returns:
        Team config dict with members, pitch, rate, etc.
    """
    config = _load_yaml(config_path)
    teams = config.get("teams", {})
    
    if team_key not in teams:
        available = list(teams.keys())
        raise KeyError(f"Team '{team_key}' not found. Available: {available}")
    
    team = teams[team_key].copy()
    team["key"] = team_key
    
    # Load member profiles as dicts
    profiles = config.get("profiles", {})
    team["member_profiles"] = [
        profiles.get(m, {}) for m in team.get("members", [])
    ]
    
    # Set primary contact details
    primary = team.get("primary_contact")
    if primary and primary in profiles:
        team["email"] = profiles[primary].get("email")
        team["phone"] = profiles[primary].get("phone")
    
    # Collect all attachments from members
    team["attachments"] = []
    for member in team.get("members", []):
        if member in profiles:
            attachments = profiles[member].get("attachments", {})
            if isinstance(attachments, dict):
                team["attachments"].extend(attachments.values())
            elif isinstance(attachments, list):
                team["attachments"].extend(attachments)
    
    return team

