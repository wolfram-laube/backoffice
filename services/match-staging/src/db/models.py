"""Database models for the Bewerbungen Pipeline.

Uses SQLAlchemy 2.0 with async support.
Backend-agnostic: works with SQLite (dev/MVP) and PostgreSQL (Cloud SQL).
"""

import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# --- Enums ---


class ApplicationStatus(str, enum.Enum):
    """Normalized application lifecycle states."""
    IDENTIFIED = "identified"           # Lead found, not yet evaluated
    STAGED = "staged"                   # In Vorhölle, awaiting review
    APPROVED = "approved"               # Approved for sending
    SENT = "sent"                       # Application sent
    AT_CLIENT = "at_client"             # Forwarded to end client
    INTERVIEW = "interview"             # Interview scheduled/completed
    IN_NEGOTIATION = "in_negotiation"   # Contract negotiation
    CONTRACT = "contract"               # Contract received/signed
    REJECTED = "rejected"               # Rejected (by us or them)
    NO_RESPONSE = "no_response"         # No response after reasonable time
    NOT_APPLIED = "not_applied"         # Decided not to apply
    WITHDRAWN = "withdrawn"             # We withdrew


class MatchTier(str, enum.Enum):
    """Match quality tiers."""
    HIGH = "high"       # ≥90%
    MEDIUM = "medium"   # 70-89%
    LOW = "low"         # <70%


class SourcePlatform(str, enum.Enum):
    """Job listing source platforms."""
    FREELANCERMAP = "freelancermap"
    GULP = "gulp"
    RANDSTAD = "randstad"
    HAYS = "hays"
    XING = "xing"
    LINKEDIN = "linkedin"
    DIRECT = "direct"
    REFERRAL = "referral"
    OTHER = "other"


# --- Models ---


class Application(Base):
    """Core application tracking table — replaces the CSV."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Timestamps ---
    date_recorded: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # --- Job Details ---
    project_title: Mapped[str] = mapped_column(String(500), nullable=False)
    provider: Mapped[str] = mapped_column(String(300), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    contact_email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    location: Mapped[Optional[str]] = mapped_column(String(300))
    start_date: Mapped[Optional[str]] = mapped_column(String(50))  # "ASAP", "02.03.2026"
    duration: Mapped[Optional[str]] = mapped_column(String(100))   # "6 Monate", "12 Mo+"
    workload: Mapped[Optional[str]] = mapped_column(String(50))    # "100%", "FT", "80-100%"
    rate_eur_h: Mapped[Optional[int]] = mapped_column(Integer, default=105)
    remote_percentage: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100

    # --- Source ---
    source_platform: Mapped[Optional[str]] = mapped_column(
        String(50), default=SourcePlatform.OTHER.value
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))
    source_ref_id: Mapped[Optional[str]] = mapped_column(String(100))  # Platform-specific ID

    # --- Status ---
    status: Mapped[str] = mapped_column(
        String(50), default=ApplicationStatus.IDENTIFIED.value, nullable=False
    )
    status_date: Mapped[Optional[date]] = mapped_column(Date)  # When status last changed
    status_detail: Mapped[Optional[str]] = mapped_column(Text)  # Free-text status notes

    # --- Match Assessment ---
    match_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    match_tier: Mapped[Optional[str]] = mapped_column(String(20))
    match_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)  # Detailed requirement scores
    strengths: Mapped[Optional[list]] = mapped_column(JSON)
    gaps: Mapped[Optional[list]] = mapped_column(JSON)

    # --- Draft ---
    draft_text: Mapped[Optional[str]] = mapped_column(Text)
    draft_variant: Mapped[Optional[str]] = mapped_column(String(50))  # "standard", "viking", etc.

    # --- GitLab Integration ---
    gitlab_issue_iid: Mapped[Optional[int]] = mapped_column(Integer)
    gitlab_issue_url: Mapped[Optional[str]] = mapped_column(String(500))

    # --- Notes ---
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # --- Relationships ---
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="application", cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at.desc()"
    )

    def __repr__(self) -> str:
        return (
            f"<Application(id={self.id}, score={self.match_score}, "
            f"status='{self.status}', title='{self.project_title[:40]}...')>"
        )


class StatusHistory(Base):
    """Audit trail for status changes — every transition is recorded."""

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id"), nullable=False
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    comment: Mapped[Optional[str]] = mapped_column(Text)
    changed_by: Mapped[Optional[str]] = mapped_column(String(100))  # "claude", "user", "system"

    application: Mapped["Application"] = relationship(back_populates="history")

    def __repr__(self) -> str:
        return (
            f"<StatusHistory({self.old_status} → {self.new_status} "
            f"at {self.changed_at})>"
        )


class MatchCycle(Base):
    """Audit trail for Search→Match→Draft cycles."""

    __tablename__ = "match_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cycle_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Search parameters
    search_params: Mapped[Optional[dict]] = mapped_column(JSON)  # keywords, platforms, filters
    leads_found: Mapped[int] = mapped_column(Integer, default=0)
    leads_qualified: Mapped[int] = mapped_column(Integer, default=0)  # Above threshold
    leads_staged: Mapped[int] = mapped_column(Integer, default=0)

    # Notification results
    notifications_sent: Mapped[Optional[dict]] = mapped_column(JSON)  # {channel: bool}

    def __repr__(self) -> str:
        return (
            f"<MatchCycle(id='{self.cycle_id}', found={self.leads_found}, "
            f"qualified={self.leads_qualified})>"
        )


# --- Runner Fleet Models ---


class RunnerExecutor(str, enum.Enum):
    """Runner executor types."""
    SHELL = "shell"
    DOCKER = "docker"
    K8S = "k8s"
    CUSTOM = "custom"


class RunnerLocation(str, enum.Enum):
    """Runner physical location."""
    MAC1 = "mac1"
    MAC2 = "mac2"
    YOGA = "yoga"
    GCP_NORDIC = "gcp_nordic"
    SHARED = "shared"


class Runner(Base):
    """Runner fleet inventory — registered GitLab runners."""

    __tablename__ = "runners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gitlab_runner_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    executor: Mapped[str] = mapped_column(String(20), default=RunnerExecutor.DOCKER.value)
    location: Mapped[str] = mapped_column(String(50), default=RunnerLocation.SHARED.value)
    tags: Mapped[Optional[list]] = mapped_column(JSON)
    cost_eur_h: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    snapshots: Mapped[list["RunnerSnapshot"]] = relationship(
        back_populates="runner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Runner(id={self.gitlab_runner_id}, name='{self.name}', executor={self.executor})>"


class RunnerSnapshot(Base):
    """Point-in-time runner status — collected periodically (e.g. every 5 min)."""

    __tablename__ = "runner_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runners.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # online/offline/paused
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))

    runner: Mapped["Runner"] = relationship(back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<RunnerSnapshot(runner={self.runner_id}, status='{self.status}', at={self.captured_at})>"


class MABObservation(Base):
    """Multi-Armed Bandit observation log — every pull recorded."""

    __tablename__ = "mab_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runner_name: Mapped[str] = mapped_column(String(200), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), default="ucb1")

    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_s: Mapped[float] = mapped_column(Float, nullable=False)
    reward: Mapped[float] = mapped_column(Float, nullable=False)

    job_name: Mapped[Optional[str]] = mapped_column(String(200))
    pipeline_id: Mapped[Optional[int]] = mapped_column(Integer)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<MABObservation(runner='{self.runner_name}', reward={self.reward:.2f}, "
            f"duration={self.duration_s:.1f}s)>"
        )
