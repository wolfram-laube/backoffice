"""SQLAlchemy 2.0 models for Application Tracking System (ADR-004).

Three tables:
- applications:         190+ bewerbungen from CSV + future crawl-matched ones
- crawl_results:        Raw crawl output from GULP/freelancermap/freelance.de
- application_history:  Audit trail for status changes
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Integer,
    Float,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    event,
    inspect,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Shared declarative base for all apptrack models."""
    pass


class Application(Base):
    """A job application — the central entity.

    Maps 1:1 to CSV rows during initial import.
    match_score is parsed from notes ("MATCH 85%!" → 85).
    """
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_recorded: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    project_title: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rate_eur_h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    match_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    history: Mapped[list["ApplicationHistory"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationHistory.changed_at.desc()",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_applications_date", "date_recorded"),
        Index("ix_applications_status", "status"),
        Index("ix_applications_provider", "provider"),
        Index("ix_applications_match_score", "match_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<Application(id={self.id}, "
            f"date={self.date_recorded}, "
            f"title='{self.project_title[:50]}...', "
            f"status='{self.status}')>"
        )


class CrawlResult(Base):
    """Raw crawl output from job portals.

    Deduplicated by (source, external_id).
    Linked to applications once a match is approved.
    """
    __tablename__ = "crawl_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # gulp / freelancermap / fl.de
    external_id: Mapped[str] = mapped_column(Text, nullable=False)  # Portal-ID
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    match_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    match_reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="new"
    )  # new / matched / applied / dismissed
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_crawl_source_extid", "source", "external_id", unique=True),
        Index("ix_crawl_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CrawlResult(id={self.id}, "
            f"source='{self.source}', "
            f"ext_id='{self.external_id}', "
            f"status='{self.status}')>"
        )


class ApplicationHistory(Base):
    """Audit trail — tracks every field change on applications."""
    __tablename__ = "application_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    field_changed: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    application: Mapped["Application"] = relationship(back_populates="history")

    __table_args__ = (
        Index("ix_history_app_id", "application_id"),
        Index("ix_history_changed_at", "changed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationHistory(app_id={self.application_id}, "
            f"field='{self.field_changed}', "
            f"'{self.old_value}' → '{self.new_value}')>"
        )


# ---------------------------------------------------------------------------
# Auto-history via SQLAlchemy event listeners
# ---------------------------------------------------------------------------
TRACKED_FIELDS = {
    "status", "match_score", "rate_eur_h", "notes",
    "contact_name", "contact_email", "location",
}


def track_application_changes(session):
    """Collect history entries for dirty Application objects.

    Call this BEFORE session.commit() or register via SessionEvents.before_flush.
    Uses attribute history to detect changed tracked fields.
    """
    changes = []
    for obj in session.dirty:
        if not isinstance(obj, Application):
            continue
        state = inspect(obj)
        for attr in TRACKED_FIELDS:
            hist = state.attrs[attr].history
            if hist.has_changes():
                old = hist.deleted[0] if hist.deleted else None
                new = hist.added[0] if hist.added else None
                changes.append(ApplicationHistory(
                    application_id=obj.id,
                    field_changed=attr,
                    old_value=str(old) if old is not None else None,
                    new_value=str(new) if new is not None else None,
                ))
    if changes:
        session.add_all(changes)
    return changes


@event.listens_for(Session, "before_flush")
def _before_flush_track_changes(session, flush_context, instances):
    """Automatically create history entries during flush."""
    track_application_changes(session)
