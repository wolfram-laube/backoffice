"""
Profile Configuration Loader
============================
Loads profile configurations from YAML.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


# Default config location (relative to module)
DEFAULT_CONFIG = Path(__file__).parent / "profiles.yaml"


def load_profiles(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load all profiles from YAML config.
    
    Args:
        config_path: Path to profiles.yaml (default: module dir)
        
    Returns:
        Full config dict with 'profiles', 'teams', 'defaults'
    """
    path = config_path or DEFAULT_CONFIG
    
    if not path.exists():
        raise FileNotFoundError(f"Profile config not found: {path}")
    
    with open(path) as f:
        return yaml.safe_load(f)


def load_profile(
    profile_key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Load a single profile by key.
    
    Args:
        profile_key: Profile identifier (e.g., 'wolfram', 'ian')
        config_path: Path to profiles.yaml
        
    Returns:
        Profile dict with name, email, rate, attachments, etc.
    """
    config = load_profiles(config_path)
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
    
    return profile


def get_team_config(
    team_key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Load team configuration.
    
    Args:
        team_key: Team identifier (e.g., 'wolfram_ian', 'all_three')
        config_path: Path to profiles.yaml
        
    Returns:
        Team config with members, pitch, rate, etc.
    """
    config = load_profiles(config_path)
    teams = config.get("teams", {})
    
    if team_key not in teams:
        available = list(teams.keys())
        raise KeyError(f"Team '{team_key}' not found. Available: {available}")
    
    team = teams[team_key].copy()
    team["key"] = team_key
    
    # Load member profiles
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
            team["attachments"].extend(profiles[member].get("attachments", []))
    
    return team


def get_profile_or_team(
    key: str,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Load profile or team by key.
    Tries profiles first, then teams.
    """
    config = load_profiles(config_path)
    
    if key in config.get("profiles", {}):
        return load_profile(key, config_path)
    elif key in config.get("teams", {}):
        return get_team_config(key, config_path)
    else:
        all_keys = list(config.get("profiles", {}).keys()) + list(config.get("teams", {}).keys())
        raise KeyError(f"'{key}' not found. Available: {all_keys}")


def list_available_profiles(config_path: Optional[Path] = None) -> Dict[str, List[str]]:
    """
    List all available profiles and teams.
    
    Returns:
        Dict with 'profiles' and 'teams' lists
    """
    config = load_profiles(config_path)
    return {
        "profiles": list(config.get("profiles", {}).keys()),
        "teams": list(config.get("teams", {}).keys()),
    }
