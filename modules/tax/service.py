"""Tax service."""
from datetime import date
from pathlib import Path
from typing import Optional


class TaxService:
    """Service for tax-related tasks."""
    
    def generate_uva(
        self,
        year: int,
        quarter: int,
    ) -> Path:
        """Generate Umsatzsteuervoranmeldung (Austrian VAT return)."""
        raise NotImplementedError
    
    def generate_euer(
        self,
        year: int,
    ) -> Path:
        """Generate Einnahmen-Überschuss-Rechnung."""
        raise NotImplementedError
    
    def collect_documents(
        self,
        year: int,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Collect all tax-relevant documents for a year."""
        raise NotImplementedError
    
    def validate_invoices(
        self,
        year: int,
    ) -> dict:
        """Validate all invoices have required tax info."""
        raise NotImplementedError
