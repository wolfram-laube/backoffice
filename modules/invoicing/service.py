"""Invoice service."""
from pathlib import Path
from typing import Optional
from datetime import date

from common.models import Project, Client


class InvoiceService:
    """Service for creating and managing invoices."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or Path(__file__).parent / 'templates'
    
    def create_invoice(
        self,
        project: Project,
        invoice_number: str,
        hours: float,
        period_start: date,
        period_end: date,
        language: str = 'de',
    ) -> Path:
        """Generate invoice PDF from Typst template."""
        # TODO: Implement Typst rendering
        # - Load template
        # - Fill in data
        # - Compile to PDF
        raise NotImplementedError('Coming soon - migrate from corporate repo')
    
    def list_invoices(self, client: Optional[Client] = None) -> list:
        """List all invoices, optionally filtered by client."""
        raise NotImplementedError
