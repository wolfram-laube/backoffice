"""Base data models."""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


class ProjectStatus(Enum):
    LEAD = 'lead'              # Potentielles Projekt
    APPLIED = 'applied'        # Bewerbung gesendet
    INTERVIEW = 'interview'    # Im Gespräch
    NEGOTIATION = 'negotiation'  # Verhandlung
    ACTIVE = 'active'          # Laufendes Projekt
    COMPLETED = 'completed'    # Abgeschlossen
    REJECTED = 'rejected'      # Abgelehnt
    CANCELLED = 'cancelled'    # Abgebrochen


@dataclass
class Contact:
    """Ansprechpartner."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None  # z.B. 'Recruiter', 'Hiring Manager'


@dataclass
class Client:
    """Kunde/Auftraggeber."""
    name: str
    address: Optional[str] = None
    vat_id: Optional[str] = None  # USt-ID
    contacts: List[Contact] = field(default_factory=list)
    
    # Abrechnungsinfos
    payment_terms: int = 30  # Zahlungsziel in Tagen
    currency: str = 'EUR'


@dataclass
class Project:
    """Projekt - verbindet Bewerbung, Timesheets, Rechnungen."""
    id: str
    title: str
    client: Client
    status: ProjectStatus = ProjectStatus.LEAD
    
    # Zeitraum
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Konditionen
    hourly_rate: Optional[float] = None
    daily_rate: Optional[float] = None
    currency: str = 'EUR'
    
    # Referenzen
    application_id: Optional[str] = None  # Link zur Bewerbung
    contract_path: Optional[str] = None   # Vertragsdokument
    
    # Meta
    source: Optional[str] = None  # z.B. 'freelancermap', 'direktkontakt'
    notes: str = ''
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
