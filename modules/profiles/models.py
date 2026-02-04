"""
Profile Models
==============
Dataclasses for profile and team configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any


@dataclass
class RateConfig:
    """Rate configuration with min/max/preferred."""
    min: int = 90
    max: int = 120
    preferred: int = 105
    
    @classmethod
    def from_dict(cls, data: Any) -> "RateConfig":
        """Create from dict or single value."""
        if isinstance(data, dict):
            return cls(
                min=data.get("min", 90),
                max=data.get("max", 120),
                preferred=data.get("preferred", 105)
            )
        elif isinstance(data, (int, str)):
            # Single value = preferred, others derived
            val = int(data)
            return cls(min=val - 15, max=val + 15, preferred=val)
        return cls()


@dataclass
class KeywordConfig:
    """Keyword categories for matching."""
    must_have: Set[str] = field(default_factory=set)
    strong_match: Set[str] = field(default_factory=set)
    nice_to_have: Set[str] = field(default_factory=set)
    exclude: Set[str] = field(default_factory=set)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "KeywordConfig":
        """Create from dict with lists."""
        return cls(
            must_have=set(data.get("must_have", [])),
            strong_match=set(data.get("strong_match", [])),
            nice_to_have=set(data.get("nice_to_have", [])),
            exclude=set(data.get("exclude", []))
        )


@dataclass
class ConstraintConfig:
    """Profile constraints."""
    remote_only: bool = True
    languages: List[str] = field(default_factory=lambda: ["Deutsch", "Englisch"])
    min_duration_months: int = 3
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ConstraintConfig":
        """Create from dict."""
        return cls(
            remote_only=data.get("remote_only", True),
            languages=data.get("languages", ["Deutsch", "Englisch"]),
            min_duration_months=data.get("min_duration_months", 3)
        )


@dataclass
class Profile:
    """A freelancer profile with all configuration."""
    key: str
    name: str
    email: str
    phone: str
    
    # Rates
    rate: RateConfig = field(default_factory=RateConfig)
    
    # Documents
    attachments: Dict[str, str] = field(default_factory=dict)
    
    # Email
    signature: str = ""
    
    # Constraints
    constraints: ConstraintConfig = field(default_factory=ConstraintConfig)
    
    # Matching
    keywords: KeywordConfig = field(default_factory=KeywordConfig)
    
    # Legacy compatibility
    @property
    def cv_de(self) -> Optional[str]:
        return self.attachments.get("cv_de")
    
    @property
    def cv_en(self) -> Optional[str]:
        return self.attachments.get("cv_en")
    
    @property
    def rate_min(self) -> int:
        return self.rate.min
    
    @property
    def rate_max(self) -> int:
        return self.rate.max
    
    @property
    def rate_preferred(self) -> int:
        return self.rate.preferred
    
    @property
    def must_have(self) -> Set[str]:
        return self.keywords.must_have
    
    @property
    def strong_match(self) -> Set[str]:
        return self.keywords.strong_match
    
    @property
    def nice_to_have(self) -> Set[str]:
        return self.keywords.nice_to_have
    
    @property
    def exclude(self) -> Set[str]:
        return self.keywords.exclude
    
    @property
    def remote_only(self) -> bool:
        return self.constraints.remote_only
    
    @property
    def languages(self) -> List[str]:
        return self.constraints.languages
    
    @property
    def min_duration_months(self) -> int:
        return self.constraints.min_duration_months
    
    def get_attachments_list(self) -> List[str]:
        """Get attachments as flat list (for gmail compatibility)."""
        return list(self.attachments.values())
    
    @classmethod
    def from_dict(cls, key: str, data: Dict) -> "Profile":
        """Create Profile from config dict."""
        return cls(
            key=key,
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            rate=RateConfig.from_dict(data.get("rate", {})),
            attachments=data.get("attachments", {}),
            signature=data.get("signature", ""),
            constraints=ConstraintConfig.from_dict(data.get("constraints", {})),
            keywords=KeywordConfig.from_dict(data.get("keywords", {}))
        )


@dataclass
class Team:
    """A team combination of profiles."""
    key: str
    name: str
    members: List[str]
    primary_contact: str
    rate: str = "verhandelbar"
    pitch: str = ""
    description: str = ""
    keywords: Set[str] = field(default_factory=set)
    
    # Resolved member profiles (populated by loader)
    member_profiles: List[Profile] = field(default_factory=list)
    
    @property
    def email(self) -> Optional[str]:
        """Get email from primary contact."""
        for p in self.member_profiles:
            if p.key == self.primary_contact:
                return p.email
        return self.member_profiles[0].email if self.member_profiles else None
    
    @property
    def phone(self) -> Optional[str]:
        """Get phone from primary contact."""
        for p in self.member_profiles:
            if p.key == self.primary_contact:
                return p.phone
        return self.member_profiles[0].phone if self.member_profiles else None
    
    def get_all_attachments(self) -> List[str]:
        """Collect all attachments from member profiles."""
        attachments = []
        for p in self.member_profiles:
            attachments.extend(p.get_attachments_list())
        return attachments
    
    @classmethod
    def from_dict(cls, key: str, data: Dict) -> "Team":
        """Create Team from config dict."""
        return cls(
            key=key,
            name=data.get("name", ""),
            members=data.get("members", []),
            primary_contact=data.get("primary_contact", ""),
            rate=data.get("rate", "verhandelbar"),
            pitch=data.get("pitch", ""),
            description=data.get("description", ""),
            keywords=set(data.get("keywords", []))
        )

