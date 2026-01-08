"""Application service - wraps existing bewerbung.py functionality."""
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from common.models import Project, ProjectStatus


@dataclass
class Application:
    """A job application."""
    id: str
    project_title: str
    company: str
    contact_email: Optional[str]
    subject: str
    body: str
    source: str  # 'freelancermap', 'email', etc.
    source_url: Optional[str]
    status: str = 'draft'
    sent_at: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class ApplicationService:
    """Service for managing job applications."""
    
    def __init__(self):
        # Import existing bewerbungen from legacy module
        from .bewerbung import BEWERBUNGEN
        self._bewerbungen = BEWERBUNGEN
    
    def list_applications(self) -> List[Application]:
        """List all configured applications."""
        return [
            Application(
                id=key,
                project_title=bew['name'],
                company=bew['name'].split(' - ')[0] if ' - ' in bew['name'] else '',
                contact_email=bew.get('to'),
                subject=bew['subject'],
                body=bew['body'],
                source='freelancermap' if bew.get('freelancermap') else 'email',
                source_url=bew.get('freelancermap'),
            )
            for key, bew in self._bewerbungen.items()
        ]
    
    def get_application(self, key: str) -> Optional[Application]:
        """Get application by key."""
        apps = {a.id: a for a in self.list_applications()}
        return apps.get(key)
    
    def create_gmail_draft(self, key: str, attachments: List[Path] = None):
        """Create Gmail draft for application."""
        from .bewerbung import create_gmail_draft, BEWERBUNGEN, select_attachments
        
        if key not in BEWERBUNGEN:
            raise ValueError(f'Unknown application: {key}')
        
        bewerbung = BEWERBUNGEN[key]
        if attachments is None:
            attachments = select_attachments()
        
        return create_gmail_draft(bewerbung, attachments)
    
    def convert_to_project(self, key: str) -> Project:
        """Convert accepted application to active project."""
        app = self.get_application(key)
        if not app:
            raise ValueError(f'Unknown application: {key}')
        
        # TODO: Create project from application
        raise NotImplementedError
