"""
DEPRECATED: Use modules.profiles instead
=========================================
This module is kept for backwards compatibility.
All functionality has been moved to modules/profiles/.

Migration:
    # Old
    from src.admin.applications.pipeline.profiles import WOLFRAM, PROFILES, TEAM_COMBOS

    # New
    from modules.profiles import WOLFRAM, PROFILES, TEAM_COMBOS
"""

import warnings
import sys
import os

# Add project root to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

# Re-export everything from new module
from modules.profiles import (
    # Models
    Profile,
    Team,
    RateConfig,
    KeywordConfig,
    ConstraintConfig,
    # Loader
    load_profile,
    load_profiles,
    load_all_profiles,
    get_team_config,
    load_all_teams,
    get_profile_or_team,
    list_available,
    # Matching
    match_profile,
    match_team,
    get_best_matches,
    get_best_team_matches,
    # Legacy constants
    WOLFRAM,
    IAN,
    MICHAEL,
    PROFILES,
    TEAM_COMBOS,
)


def _show_deprecation_once():
    """Show deprecation warning once per session."""
    if not getattr(_show_deprecation_once, "_warned", False):
        warnings.warn(
            "src.admin.applications.pipeline.profiles is deprecated. "
            "Use modules.profiles instead.",
            DeprecationWarning,
            stacklevel=3
        )
        _show_deprecation_once._warned = True


# Show warning on import
_show_deprecation_once()


__all__ = [
    "Profile",
    "Team", 
    "RateConfig",
    "KeywordConfig",
    "ConstraintConfig",
    "load_profile",
    "load_profiles",
    "load_all_profiles",
    "get_team_config",
    "load_all_teams",
    "get_profile_or_team",
    "list_available",
    "match_profile",
    "match_team",
    "get_best_matches",
    "get_best_team_matches",
    "WOLFRAM",
    "IAN",
    "MICHAEL",
    "PROFILES",
    "TEAM_COMBOS",
]

