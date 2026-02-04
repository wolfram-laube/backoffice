"""
Profiles Module
===============
Centralized profile management for Blauweiss LLC.

This module provides:
- Profile and Team dataclasses
- YAML-based configuration loading
- Keyword-based matching for job descriptions
- Legacy compatibility with gmail/profiles.py and pipeline/profiles.py

Usage:
    from modules.profiles import (
        # Objects
        Profile, Team,
        # Loading
        load_profile, load_all_profiles,
        get_team_config, load_all_teams,
        get_profile_or_team, list_available,
        # Matching
        match_profile, match_team,
        get_best_matches, get_best_team_matches,
    )

    # Load a profile
    wolfram = load_profile("wolfram")
    print(wolfram.email)  # wolfram.laube@blauweiss-edv.at
    print(wolfram.rate.preferred)  # 105

    # Match against job description
    from modules.profiles import match_profile
    result = match_profile(wolfram, job_text)
    print(result["percentage"])  # 85

Legacy compatibility:
    # These still work for backwards compatibility:
    from modules.profiles import WOLFRAM, IAN, MICHAEL, PROFILES, TEAM_COMBOS
"""

# Models
from .models import (
    Profile,
    Team,
    RateConfig,
    KeywordConfig,
    ConstraintConfig,
)

# Loader functions
from .loader import (
    load_profile,
    load_profiles,
    load_all_profiles,
    get_team_config,
    load_all_teams,
    get_profile_or_team,
    list_available,
    clear_cache,
    # Legacy dict-based API
    load_profile_dict,
    get_team_config_dict,
)

# Matching functions
from .matching import (
    match_profile,
    match_team,
    get_best_matches,
    get_best_team_matches,
)


# =============================================================================
# LEGACY CONSTANTS (for backwards compatibility with pipeline/profiles.py)
# =============================================================================

# Lazy-loaded profile instances
_profile_cache = {}

def _get_profile(key: str) -> Profile:
    """Get cached profile instance."""
    if key not in _profile_cache:
        _profile_cache[key] = load_profile(key)
    return _profile_cache[key]


# Legacy profile constants - these add match_score method
class _LegacyProfileWrapper:
    """Wrapper that adds match_score method for backwards compatibility."""
    
    def __init__(self, key: str):
        self._key = key
        self._profile = None
    
    def _ensure_loaded(self):
        if self._profile is None:
            self._profile = load_profile(self._key)
    
    def __getattr__(self, name):
        self._ensure_loaded()
        return getattr(self._profile, name)
    
    def match_score(self, text: str):
        """Legacy match_score method."""
        self._ensure_loaded()
        return match_profile(self._profile, text)


# Create legacy-compatible profile objects
WOLFRAM = _LegacyProfileWrapper("wolfram")
IAN = _LegacyProfileWrapper("ian")
MICHAEL = _LegacyProfileWrapper("michael")


# Legacy PROFILES dict
class _ProfilesDict(dict):
    """Lazy-loading profiles dict."""
    
    def __init__(self):
        super().__init__()
        self._loaded = False
    
    def _ensure_loaded(self):
        if not self._loaded:
            self["wolfram"] = WOLFRAM
            self["ian"] = IAN
            self["michael"] = MICHAEL
            self._loaded = True
    
    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)
    
    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)
    
    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()
    
    def __len__(self):
        self._ensure_loaded()
        return super().__len__()
    
    def items(self):
        self._ensure_loaded()
        return super().items()
    
    def keys(self):
        self._ensure_loaded()
        return super().keys()
    
    def values(self):
        self._ensure_loaded()
        return super().values()


PROFILES = _ProfilesDict()


# Legacy TEAM_COMBOS - loaded from config
class _TeamCombosDict(dict):
    """Lazy-loading team combos dict."""
    
    def __init__(self):
        super().__init__()
        self._loaded = False
    
    def _ensure_loaded(self):
        if not self._loaded:
            teams = load_all_teams()
            for key, team in teams.items():
                self[key] = {
                    "name": team.name,
                    "profiles": [PROFILES[m] for m in team.members],
                    "keywords": team.keywords,
                    "description": team.description,
                }
            self._loaded = True
    
    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)
    
    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)
    
    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()
    
    def __len__(self):
        self._ensure_loaded()
        return super().__len__()
    
    def items(self):
        self._ensure_loaded()
        return super().items()
    
    def keys(self):
        self._ensure_loaded()
        return super().keys()
    
    def values(self):
        self._ensure_loaded()
        return super().values()


TEAM_COMBOS = _TeamCombosDict()


__all__ = [
    # Models
    "Profile",
    "Team",
    "RateConfig",
    "KeywordConfig",
    "ConstraintConfig",
    # Loader
    "load_profile",
    "load_profiles",
    "load_all_profiles",
    "get_team_config",
    "load_all_teams",
    "get_profile_or_team",
    "list_available",
    "clear_cache",
    "load_profile_dict",
    "get_team_config_dict",
    # Matching
    "match_profile",
    "match_team",
    "get_best_matches",
    "get_best_team_matches",
    # Legacy constants
    "WOLFRAM",
    "IAN",
    "MICHAEL",
    "PROFILES",
    "TEAM_COMBOS",
]

