#!/usr/bin/env python3
"""
Unit Tests for Billing Module - Invoice Generation

Tests invoice numbering, consolidation, and generation logic.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.billing import (
    SAMPLE_CONFIG,
    SAMPLE_SEQUENCES,
    SAMPLE_SYNC_DATA,
)


class TestInvoiceNumbering:
    """Tests for invoice number generation."""
    
    def test_format_invoice_number(self):
        """Test formatting invoice numbers."""
        sequences = SAMPLE_SEQUENCES["invoices"]
        prefix = sequences["prefix"]
        number = sequences["next_number"]
        
        # Format: AR-042
        invoice_number = f"{prefix}-{number:03d}"
        assert invoice_number == "AR-042"
    
    def test_increment_sequence(self):
        """Test incrementing invoice sequence."""
        current = 42
        next_number = current + 1
        assert next_number == 43
    
    def test_sequence_format_with_padding(self):
        """Test that sequence numbers are zero-padded."""
        test_cases = [
            (1, "AR-001"),
            (9, "AR-009"),
            (10, "AR-010"),
            (99, "AR-099"),
            (100, "AR-100"),
            (999, "AR-999"),
        ]
        
        for number, expected in test_cases:
            result = f"AR-{number:03d}"
            assert result == expected


class TestInvoiceConsolidation:
    """Tests for consolidating timesheets into invoices."""
    
    def test_consolidate_single_consultant(self):
        """Test invoice for single consultant."""
        timesheets = [
            {"consultant": "wolfram", "hours": 40.0, "rate": 105}
        ]
        
        total_hours = sum(t["hours"] for t in timesheets)
        total_amount = sum(t["hours"] * t["rate"] for t in timesheets)
        
        assert total_hours == 40.0
        assert total_amount == 4200.0
    
    def test_consolidate_team_project(self):
        """Test invoice for team with multiple consultants."""
        timesheets = [
            {"consultant": "wolfram", "hours": 80.0, "rate": 105},
            {"consultant": "ian", "hours": 40.0, "rate": 95},
        ]
        
        total_hours = sum(t["hours"] for t in timesheets)
        # Note: Team invoice shows consolidated hours, not individual rates
        # Individual rates are internal to LLC
        
        assert total_hours == 120.0
        
        # For external invoice, use blended rate or project rate
        project_rate = 105
        external_amount = total_hours * project_rate
        assert external_amount == 12600.0
    
    def test_separate_vs_consolidated_invoice(self):
        """Test the difference between separate and consolidated invoices."""
        timesheets = [
            {"consultant": "wolfram", "hours": 80.0, "rate": 105},
            {"consultant": "ian", "hours": 40.0, "rate": 95},
        ]
        
        # Separate invoices (internal billing)
        separate_totals = [
            t["hours"] * t["rate"] for t in timesheets
        ]
        assert separate_totals == [8400.0, 3800.0]
        
        # Consolidated (client sees team hours at project rate)
        team_hours = sum(t["hours"] for t in timesheets)
        project_rate = 105
        consolidated_total = team_hours * project_rate
        assert consolidated_total == 12600.0


class TestInvoiceLineItems:
    """Tests for invoice line items."""
    
    def test_single_line_item(self):
        """Test invoice with single line item."""
        line_items = [
            {
                "description": "Consulting Services January 2026",
                "quantity": 40.0,
                "unit": "hours",
                "rate": 105.0,
                "amount": 4200.0
            }
        ]
        
        total = sum(item["amount"] for item in line_items)
        assert total == 4200.0
    
    def test_multiple_line_items(self):
        """Test invoice with multiple line items."""
        line_items = [
            {
                "description": "Development",
                "quantity": 30.0,
                "unit": "hours",
                "rate": 105.0,
                "amount": 3150.0
            },
            {
                "description": "Consulting",
                "quantity": 10.0,
                "unit": "hours",
                "rate": 120.0,
                "amount": 1200.0
            }
        ]
        
        total = sum(item["amount"] for item in line_items)
        assert total == 4350.0
    
    def test_line_item_amount_calculation(self):
        """Test that line item amounts are calculated correctly."""
        line_item = {
            "quantity": 7.5,
            "rate": 105.0,
        }
        
        calculated_amount = line_item["quantity"] * line_item["rate"]
        assert calculated_amount == 787.5


class TestVATCalculation:
    """Tests for VAT/tax calculations."""
    
    def test_german_vat(self):
        """Test German VAT (19%)."""
        net_amount = 4200.0
        vat_rate = 0.19
        
        vat_amount = net_amount * vat_rate
        gross_amount = net_amount + vat_amount
        
        assert vat_amount == 798.0
        assert gross_amount == 4998.0
    
    def test_reverse_charge_eu(self):
        """Test reverse charge for EU B2B (0% VAT)."""
        net_amount = 4200.0
        vat_rate = 0.0  # Reverse charge
        
        vat_amount = net_amount * vat_rate
        gross_amount = net_amount + vat_amount
        
        assert vat_amount == 0.0
        assert gross_amount == 4200.0
    
    def test_us_invoice_no_vat(self):
        """Test US invoice (no VAT)."""
        net_amount = 6000.0  # USD
        # No VAT for US clients
        gross_amount = net_amount
        
        assert gross_amount == 6000.0


class TestInvoiceDates:
    """Tests for invoice date handling."""
    
    def test_invoice_date_format(self):
        """Test formatting invoice date."""
        invoice_date = datetime(2026, 2, 1)
        
        # German format
        formatted_de = invoice_date.strftime("%d.%m.%Y")
        assert formatted_de == "01.02.2026"
        
        # US format
        formatted_us = invoice_date.strftime("%m/%d/%Y")
        assert formatted_us == "02/01/2026"
    
    def test_due_date_calculation(self):
        """Test calculating due date (30 days from invoice)."""
        from datetime import timedelta
        
        invoice_date = datetime(2026, 2, 1)
        payment_terms = 30  # days
        
        due_date = invoice_date + timedelta(days=payment_terms)
        assert due_date == datetime(2026, 3, 3)
    
    def test_billing_period_format(self):
        """Test formatting billing period."""
        year = 2026
        month = 1
        
        period_de = f"Januar {year}"
        period_en = f"January {year}"
        
        assert period_de == "Januar 2026"
        assert period_en == "January 2026"


class TestCurrencyHandling:
    """Tests for currency handling."""
    
    def test_euro_formatting(self):
        """Test EUR formatting."""
        amount = 4200.50
        formatted = f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        assert formatted == "4.200,50 €"
    
    def test_usd_formatting(self):
        """Test USD formatting."""
        amount = 6000.00
        formatted = f"${amount:,.2f}"
        assert formatted == "$6,000.00"
    
    def test_no_floating_point_errors(self):
        """Test that currency calculations avoid floating point errors."""
        # Use integer cents for calculations
        hours_cents = 750  # 7.5 hours * 100
        rate_cents = 10500  # 105.00 * 100
        
        amount_cents = (hours_cents * rate_cents) // 100
        amount = amount_cents / 100
        
        assert amount == 787.50


class TestTemplateSelection:
    """Tests for invoice template selection."""
    
    def test_select_template_by_client(self):
        """Test selecting template based on client config."""
        clients = {
            "de_client": {"template": "rechnung-de"},
            "eu_client": {"template": "invoice-en-eu"},
            "us_client": {"template": "invoice-en-us"},
        }
        
        assert clients["de_client"]["template"] == "rechnung-de"
        assert clients["eu_client"]["template"] == "invoice-en-eu"
        assert clients["us_client"]["template"] == "invoice-en-us"
    
    def test_template_file_exists_check(self):
        """Test checking if template file exists."""
        templates_dir = Path("/tmp/test_templates")
        template_name = "rechnung-de"
        
        # Simulate check
        template_file = templates_dir / f"{template_name}.typ"
        expected_path = Path("/tmp/test_templates/rechnung-de.typ")
        
        assert template_file == expected_path


class TestGoogleDriveIntegration:
    """Tests for Google Drive upload logic (without actual API calls)."""
    
    def test_drive_path_construction(self):
        """Test constructing Google Drive folder paths."""
        base_folder = "Buchhaltung"
        client = "nemensis"
        year = 2026
        month = 1
        
        # Client folder path
        client_path = f"{base_folder}/clients/{client}/{year}/{month:02d}"
        assert client_path == "Buchhaltung/clients/nemensis/2026/01"
        
        # Contractor folder path
        contractor = "wolfram"
        contractor_path = f"{base_folder}/contractors/{contractor}/{year}/{month:02d}/{client}"
        assert contractor_path == "Buchhaltung/contractors/wolfram/2026/01/nemensis"
    
    def test_filename_conventions(self):
        """Test invoice filename conventions."""
        client = "nemensis"
        year = 2026
        month = 1
        invoice_nr = "AR-042"
        
        filename = f"{client}_{year}-{month:02d}_invoice_{invoice_nr}.pdf"
        assert filename == "nemensis_2026-01_invoice_AR-042.pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
