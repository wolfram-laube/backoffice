"""Controlling service."""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Dict
from decimal import Decimal


@dataclass
class FinancialSummary:
    """Financial summary for a period."""
    period_start: date
    period_end: date
    
    revenue: Decimal
    invoiced: Decimal
    received: Decimal
    outstanding: Decimal
    
    hours_worked: float
    hours_billable: float
    
    effective_hourly_rate: Decimal
    
    by_client: Dict[str, Decimal] = None
    by_project: Dict[str, Decimal] = None


class ControllingService:
    """Service for financial analysis and reporting."""
    
    def get_summary(
        self,
        period_start: date,
        period_end: date,
    ) -> FinancialSummary:
        """Get financial summary for period."""
        raise NotImplementedError
    
    def get_revenue_forecast(
        self,
        months: int = 3,
    ) -> List[Dict]:
        """Forecast revenue based on active projects."""
        raise NotImplementedError
    
    def get_tax_estimate(
        self,
        year: int,
    ) -> Dict:
        """Estimate tax liability for year."""
        raise NotImplementedError
    
    def export_for_accountant(
        self,
        year: int,
        format: str = 'csv',
    ):
        """Export data for accountant/Steuerberater."""
        raise NotImplementedError
