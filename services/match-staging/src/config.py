"""Configuration management for notification channels and preferences.

Loads from YAML config file with environment variable overrides.
Pattern: CONFIG__{SECTION}__{KEY} overrides nested YAML keys.
Example: CONFIG__NOTIFICATION__CHANNELS__SLACK__ENABLED=true
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


# --- Channel Configs ---


class EmailConfig(BaseModel):
    enabled: bool = True
    recipients: list[str] = ["wolfram.laube@blauweiss-edv.at"]
    template: str = "match_summary"


class SlackConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    channel: str = "#job-matches"


class WhatsAppConfig(BaseModel):
    enabled: bool = False
    provider: str = "twilio"
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""  # Twilio sandbox or WhatsApp Business number
    to_number: str = "+436644011521"


class GitLabToDoConfig(BaseModel):
    enabled: bool = True
    assignee_id: int = 1349601  # wolfram.laube


class ChannelsConfig(BaseModel):
    email: EmailConfig = EmailConfig()
    slack: SlackConfig = SlackConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()
    gitlab_todo: GitLabToDoConfig = GitLabToDoConfig()


# --- Preferences ---


class QuietHours(BaseModel):
    start: str = "22:00"
    end: str = "07:00"
    timezone: str = "Europe/Vienna"


class Preferences(BaseModel):
    threshold: int = Field(default=70, ge=0, le=100, description="Min score to stage")
    quiet_hours: QuietHours = QuietHours()
    batch_mode: bool = True  # batch notifications per cycle
    batch_summary: bool = True  # single summary vs per-match


class NotificationConfig(BaseModel):
    channels: ChannelsConfig = ChannelsConfig()
    preferences: Preferences = Preferences()


# --- GitLab Config ---


class GitLabConfig(BaseModel):
    base_url: str = "https://gitlab.com/api/v4"
    project_id: int = 77555895  # backoffice repo
    private_token: str = ""  # from env: GITLAB_PRIVATE_TOKEN
    labels_prefix: str = "job-match"


# --- Service Config ---


class ServiceConfig(BaseModel):
    gitlab: GitLabConfig = GitLabConfig()
    notification: NotificationConfig = NotificationConfig()
    profile_path: str = "assets/Profil_Laube_w_Summary_DE.pdf"
    cv_path: str = "assets/CV_Laube.pdf"


def _apply_env_overrides(config_dict: dict, prefix: str = "CONFIG") -> dict:
    """Apply environment variable overrides to config dict.

    Pattern: CONFIG__SECTION__KEY=value maps to config[section][key] = value
    """
    for key, value in os.environ.items():
        if not key.startswith(f"{prefix}__"):
            continue
        parts = key[len(prefix) + 2 :].lower().split("__")
        target = config_dict
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        # Type coercion for common cases
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        target[parts[-1]] = value
    return config_dict


def load_config(
    config_path: Optional[str] = None,
) -> ServiceConfig:
    """Load configuration from YAML file with env overrides.

    Priority: env vars > YAML file > defaults
    """
    config_dict = {}

    # 1. Load YAML if exists
    if config_path is None:
        config_path = os.getenv(
            "CONFIG_PATH", "config/notification-channels.yml"
        )
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            config_dict = yaml.safe_load(f) or {}

    # 2. Apply env overrides
    config_dict = _apply_env_overrides(config_dict)

    # 3. GitLab token from dedicated env var (common pattern)
    if "gitlab" not in config_dict:
        config_dict["gitlab"] = {}
    if not config_dict["gitlab"].get("private_token"):
        config_dict["gitlab"]["private_token"] = os.getenv(
            "GITLAB_PRIVATE_TOKEN", ""
        )

    return ServiceConfig(**config_dict)


# Singleton for the service
_config: Optional[ServiceConfig] = None


def get_config() -> ServiceConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> ServiceConfig:
    global _config
    _config = load_config(config_path)
    return _config
