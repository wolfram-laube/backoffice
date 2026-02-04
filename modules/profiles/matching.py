"""
Profile Matching
================
Score calculation for profile-to-job matching.
"""

from typing import Dict, List, Optional, Set, Any
from pathlib import Path

from .models import Profile, Team
from .loader import load_all_profiles, load_all_teams


def match_profile(profile: Profile, text: str) -> Dict[str, Any]:
    """
    Calculate match score for a profile against text.
    
    Args:
        profile: Profile to match
        text: Job description / project text
        
    Returns:
        Dict with score, percentage, matches, excluded_by
    """
    text_lower = text.lower()
    
    # Check exclusions first
    for kw in profile.keywords.exclude:
        if kw.lower() in text_lower:
            return {
                "score": 0,
                "percentage": 0,
                "excluded_by": kw,
                "matches": {"must_have": [], "strong_match": [], "nice_to_have": []}
            }
    
    matches = {"must_have": [], "strong_match": [], "nice_to_have": []}
    score = 0
    
    # Must-have: weight 3
    for kw in profile.keywords.must_have:
        if kw.lower() in text_lower:
            matches["must_have"].append(kw)
            score += 3
    
    # Strong match: weight 2
    for kw in profile.keywords.strong_match:
        if kw.lower() in text_lower:
            matches["strong_match"].append(kw)
            score += 2
    
    # Nice to have: weight 1
    for kw in profile.keywords.nice_to_have:
        if kw.lower() in text_lower:
            matches["nice_to_have"].append(kw)
            score += 1
    
    # Percentage calculation
    # A good project matches ~5-10 must-haves, ~3-5 strong, ~2-3 nice
    # That would be: 5*3 + 4*2 + 2*1 = 25 points = 100%
    realistic_max = 25
    percentage = min(100, int((score / realistic_max) * 100))
    
    # Bonus if many must_have match
    if profile.keywords.must_have:
        must_have_ratio = len(matches["must_have"]) / min(8, len(profile.keywords.must_have) // 5 or 1)
        if must_have_ratio >= 0.5:
            percentage = min(100, percentage + 10)
    
    return {
        "score": score,
        "percentage": percentage,
        "matches": matches,
        "excluded_by": None
    }


def match_team(team: Team, text: str) -> Dict[str, Any]:
    """
    Calculate match score for a team against text.
    
    Args:
        team: Team to match
        text: Job description / project text
        
    Returns:
        Dict with score, percentage, matches
    """
    text_lower = text.lower()
    
    matches = []
    for kw in team.keywords:
        if kw.lower() in text_lower:
            matches.append(kw)
    
    # Score based on number of keyword matches
    if len(matches) >= 6:
        percentage = min(100, 70 + (len(matches) - 6) * 5)
    elif len(matches) >= 3:
        percentage = 50 + (len(matches) - 3) * 7
    elif len(matches) >= 1:
        percentage = 20 + (len(matches) - 1) * 15
    else:
        percentage = 0
    
    return {
        "score": len(matches),
        "percentage": percentage,
        "matches": matches,
        "excluded_by": None
    }


def get_best_matches(
    text: str,
    min_percentage: int = 30,
    config_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Find the best profile matches for a text.
    
    Args:
        text: Job description / project text
        min_percentage: Minimum percentage to include
        config_path: Path to config.yaml
        
    Returns:
        List of match results sorted by score
    """
    profiles = load_all_profiles(config_path)
    results = []
    
    for key, profile in profiles.items():
        match = match_profile(profile, text)
        if match["percentage"] >= min_percentage and not match["excluded_by"]:
            results.append({
                "profile": key,
                "name": profile.name,
                **match
            })
    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_best_team_matches(
    text: str,
    min_percentage: int = 30,
    config_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Find the best team matches for a text.
    
    Args:
        text: Job description / project text
        min_percentage: Minimum percentage to include
        config_path: Path to config.yaml
        
    Returns:
        List of team match results sorted by score
    """
    teams = load_all_teams(config_path)
    results = []
    
    for key, team in teams.items():
        match = match_team(team, text)
        if match["percentage"] >= min_percentage:
            results.append({
                "team": key,
                "name": team.name,
                "members": team.members,
                **match
            })
    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# =============================================================================
# Legacy API (Profile.match_score compatible)
# =============================================================================

# This allows: profile.match_score(text) via Profile method
# See models.py - the method can delegate here if needed

