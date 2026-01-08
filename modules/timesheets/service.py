"""Timesheet service."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional
from pathlib import Path

from common.models import Project


@dataclass
class TimeEntry:
    """Single time entry."""
    project_id: str
    date: date
    hours: float
    description: str
    billable: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class TimesheetService:
    """Service for tracking and reporting time."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent / 'data'
        self.data_dir.mkdir(exist_ok=True)
    
    def log_time(
        self,
        project: Project,
        hours: float,
        description: str,
        entry_date: Optional[date] = None,
        billable: bool = True,
    ) -> TimeEntry:
        """Log time for a project."""
        entry = TimeEntry(
            project_id=project.id,
            date=entry_date or date.today(),
            hours=hours,
            description=description,
            billable=billable,
        )
        # TODO: Persist to file/DB
        return entry
    
    def get_entries(
        self,
        project: Optional[Project] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[TimeEntry]:
        """Get time entries with optional filters."""
        raise NotImplementedError
    
    def generate_report(
        self,
        project: Project,
        period_start: date,
        period_end: date,
        format: str = 'pdf',
    ) -> Path:
        """Generate timesheet report."""
        raise NotImplementedError
    
    def get_total_hours(
        self,
        project: Project,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        billable_only: bool = True,
    ) -> float:
        """Get total hours for a project."""
        raise NotImplementedError
