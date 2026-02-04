# Profiles Module

Centralized profile management for Blauweiss LLC freelancer matching and email generation.

## Overview

This module consolidates two previously separate profile systems:
- `src/admin/applications/pipeline/profiles.py` (keyword matching)
- `modules/gmail/profiles.py` + `.yaml` (email generation)

## Structure

```
modules/profiles/
├── __init__.py     # Public API and legacy compatibility
├── config.yaml     # Single source of truth
├── models.py       # Profile/Team dataclasses
├── loader.py       # YAML loading functions
├── matching.py     # Score calculation
└── README.md       # This file
```

## Usage

### Basic Loading

```python
from modules.profiles import load_profile, load_all_profiles

# Load single profile
wolfram = load_profile("wolfram")
print(wolfram.name)           # "Wolfram Laube"
print(wolfram.email)          # "wolfram.laube@blauweiss-edv.at"
print(wolfram.rate.preferred) # 105

# Load all profiles
profiles = load_all_profiles()
for key, profile in profiles.items():
    print(f"{key}: {profile.name}")
```

### Team Loading

```python
from modules.profiles import get_team_config, load_all_teams

# Load single team
team = get_team_config("wolfram_ian")
print(team.name)           # "Wolfram Laube & Ian Matejka"
print(team.pitch)          # "AI-fokussiertes Team..."
print(team.member_profiles) # [Profile, Profile]

# Load all teams
teams = load_all_teams()
```

### Matching

```python
from modules.profiles import load_profile, match_profile, get_best_matches

# Match single profile
wolfram = load_profile("wolfram")
result = match_profile(wolfram, job_description)
print(result["percentage"])  # 85
print(result["matches"])     # {"must_have": [...], "strong_match": [...]}

# Find best matches
matches = get_best_matches(job_description, min_percentage=50)
for m in matches:
    print(f"{m['name']}: {m['percentage']}%")
```

### Legacy Compatibility

The following imports still work for backwards compatibility:

```python
# Old pipeline/profiles.py style
from modules.profiles import WOLFRAM, IAN, MICHAEL, PROFILES, TEAM_COMBOS

result = WOLFRAM.match_score(text)  # Works!

# Old gmail/profiles.py style  
from modules.profiles import load_profile_dict, get_team_config_dict

profile = load_profile_dict("wolfram")  # Returns dict instead of Profile
```

## Configuration

Edit `config.yaml` to update profiles. The schema is:

```yaml
profiles:
  wolfram:
    name: "Wolfram Laube"
    email: "..."
    phone: "..."
    rate:
      min: 90
      max: 120
      preferred: 105
    attachments:
      cv_de: "..."
      cv_en: "..."
    signature: |
      Mit freundlichen Grüßen,
      ...
    constraints:
      remote_only: true
      languages: [Deutsch, Englisch]
      min_duration_months: 3
    keywords:
      must_have: [...]
      strong_match: [...]
      nice_to_have: [...]
      exclude: [...]

teams:
  wolfram_ian:
    members: [wolfram, ian]
    name: "..."
    primary_contact: wolfram
    pitch: "..."
    keywords: [...]
```

## Migration from Old System

### For `scripts/ci/applications_match.py`

```python
# Old
from src.admin.applications.pipeline.profiles import PROFILES, TEAM_COMBOS, WOLFRAM

# New (drop-in replacement)
from modules.profiles import PROFILES, TEAM_COMBOS, WOLFRAM
```

### For `modules/gmail/drafter.py`

```python
# Old
from .profiles import load_profile, get_team_config

# New
from modules.profiles import load_profile_dict as load_profile
from modules.profiles import get_team_config_dict as get_team_config
```

## Related Issues

- #387: Profile-Module konsolidieren

