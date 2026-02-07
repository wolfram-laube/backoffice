"""Pydantic models for the Job Match Staging & Notification Service."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class MatchState(str, Enum):
    """State machine for match lifecycle."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class MatchScore(str, Enum):
    """Score tier for labeling."""

    HIGH = "high"  # ≥90%
    MEDIUM = "medium"  # 70-89%


class RequirementMatch(BaseModel):
    """Single requirement and its match assessment."""

    requirement: str = Field(..., description="Requirement text from job posting")
    years_required: Optional[int] = None
    years_actual: Optional[int] = None
    score: int = Field(..., ge=0, le=100, description="Match percentage for this req")
    notes: str = ""


class JobMatch(BaseModel):
    """A single matched job lead."""

    # Core identifiers
    title: str
    provider: str
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None

    # Job details
    location: str
    remote_percentage: Optional[int] = Field(None, ge=0, le=100)
    start_date: str  # "ASAP", "01.03.2026", etc.
    duration: str  # "6 Mo", "12 Mo+", etc.
    rate_eur: int = 105
    source_url: Optional[str] = None
    source_platform: Optional[str] = None  # freelancermap, gulp, etc.

    # Match assessment
    overall_score: int = Field(..., ge=0, le=100)
    requirements: list[RequirementMatch] = []
    strengths: list[str] = []
    gaps: list[str] = []
    notes: str = ""

    # Draft
    draft_text: Optional[str] = None
    draft_variant: Optional[str] = None  # "technical", "compact", "viking"

    @property
    def score_tier(self) -> MatchScore:
        return MatchScore.HIGH if self.overall_score >= 90 else MatchScore.MEDIUM

    @property
    def score_emoji(self) -> str:
        return "🔥" if self.overall_score >= 90 else "✅"


class StagingRequest(BaseModel):
    """Request to stage one or more matches."""

    cycle_id: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    matches: list[JobMatch]
    attach_profile: bool = True
    attach_cv: bool = False
    auto_notify: bool = True


class StagedMatch(BaseModel):
    """A match that has been staged in GitLab."""

    match: JobMatch
    gitlab_issue_id: int
    gitlab_issue_iid: int
    gitlab_issue_url: str
    state: MatchState = MatchState.PENDING
    staged_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None


class StagingResponse(BaseModel):
    """Response after staging matches."""

    cycle_id: str
    staged: list[StagedMatch]
    notifications_sent: list[str] = []  # channel names
    errors: list[str] = []


class NotificationPayload(BaseModel):
    """Payload sent to notification channels."""

    cycle_id: str
    matches_count: int
    matches: list[JobMatch]
    summary: str
    review_url: str  # GitLab issues filtered by label
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_staged(
        cls, cycle_id: str, staged: list[StagedMatch], review_url: str
    ) -> "NotificationPayload":
        matches = [s.match for s in staged]
        top = max(matches, key=lambda m: m.overall_score)
        summary_lines = [
            f"{m.score_emoji} {m.overall_score}% {m.title} ({m.provider})"
            for m in sorted(matches, key=lambda m: m.overall_score, reverse=True)
        ]
        summary = (
            f"{len(matches)} neue Matches: " + ", ".join(summary_lines)
        )
        return cls(
            cycle_id=cycle_id,
            matches_count=len(matches),
            matches=matches,
            summary=summary,
            review_url=review_url,
        )


class StateTransition(BaseModel):
    """Request to transition a match to a new state."""

    new_state: MatchState
    comment: Optional[str] = None
