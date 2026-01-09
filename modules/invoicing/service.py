#!/usr/bin/env python3
"""
INVOICING SERVICE
=================
Generates invoices from Typst templates.

Usage:
  from modules.invoicing import InvoiceService
  
  svc = InvoiceService()
  svc.create_invoice(
      invoice_nr="AR001_2026",
      customer_name="ACME Corp",
      customer_vat_id="DE123456789",
      line_items=[("Consulting", 40, "hrs", 105.00)],
      template="en-eu"
  )
"""

import subprocess
import os
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Paths relative to module
MODULE_DIR = Path(__file__).parent
TEMPLATES_DIR = MODULE_DIR / "templates"
OUTPUT_DIR = MODULE_DIR / "output"
FONTS_DIR = MODULE_DIR / "fonts"


@dataclass
class InvoiceItem:
    description: str
    quantity: float
    unit: str
    unit_price: float
    
    @property
    def total(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Customer:
    name: str
    address: str
    city: str
    country: str
    vat_id: str
    reg_nr: Optional[str] = None


@dataclass
class Invoice:
    invoice_nr: str
    invoice_date: datetime
    customer: Customer
    line_items: List[InvoiceItem]
    project_nr: Optional[str] = None
    discount_text: Optional[str] = "3% discount for immediate payment (1-2 days)"
    
    @property
    def subtotal(self) -> float:
        return sum(item.total for item in self.line_items)
    
    @property
    def vat_amount(self) -> float:
        # Reverse charge = 0% VAT for EU B2B
        return 0.0
    
    @property
    def total(self) -> float:
        return self.subtotal + self.vat_amount


class InvoiceService:
    """Service for generating invoices using Typst templates."""
    
    def __init__(self, templates_dir: Path = None, output_dir: Path = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _check_typst(self) -> bool:
        """Check if Typst is installed."""
        try:
            subprocess.run(["typst", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _generate_typst_content(self, invoice: Invoice, template: str = "en-eu") -> str:
        """Generate Typst file content from invoice data."""
        
        # Read template
        template_file = self.templates_dir / f"invoice-{template}.typ"
        if not template_file.exists():
            raise FileNotFoundError(f"Template not found: {template_file}")
        
        template_content = template_file.read_text()
        
        # Format line items for Typst
        items_typst = ",\n  ".join([
            f'("{item.description}", {item.quantity:.2f}, "{item.unit}", {item.unit_price:.2f})'
            for item in invoice.line_items
        ])
        
        # Replace variables in template
        replacements = {
            'invoice_nr': f'"{invoice.invoice_nr}"',
            'invoice_date': f'"{invoice.invoice_date.strftime("%B %d, %Y")}"',
            'project_nr': f'"{invoice.project_nr or ""}"',
            'customer_name': f'"{invoice.customer.name}"',
            'customer_address': f'"{invoice.customer.address}"',
            'customer_city': f'"{invoice.customer.city}"',
            'customer_country': f'"{invoice.customer.country}"',
            'customer_vat_id': f'"{invoice.customer.vat_id}"',
            'customer_reg_nr': f'"{invoice.customer.reg_nr or ""}"',
        }
        
        content = template_content
        for key, value in replacements.items():
            pattern = rf'#let {key} = "[^"]*"'
            replacement = f'#let {key} = {value}'
            content = re.sub(pattern, replacement, content)
        
        # Replace line items (handle nested parentheses)
        content = re.sub(
            r'#let line_items = \([\s\S]*?\n\)',
            f'#let line_items = (\n  {items_typst}\n)',
            content
        )
        
        return content
    
    def create_invoice(
        self,
        invoice_nr: str,
        customer_name: str,
        customer_address: str,
        customer_city: str,
        customer_country: str,
        customer_vat_id: str,
        line_items: List[Tuple[str, float, str, float]],
        invoice_date: datetime = None,
        project_nr: str = None,
        template: str = "en-eu",
        customer_reg_nr: str = None,
    ) -> Path:
        """
        Create an invoice PDF.
        
        Args:
            invoice_nr: Invoice number (e.g., "AR001_2026")
            customer_name: Customer company name
            customer_address: Street address
            customer_city: City + postal code
            customer_country: Country
            customer_vat_id: VAT ID for reverse charge
            line_items: List of (description, quantity, unit, unit_price) tuples
            invoice_date: Date of invoice (default: today)
            project_nr: Optional project reference
            template: Template to use ("en-eu" or "de")
            
        Returns:
            Path to generated PDF
        """
        if not self._check_typst():
            raise RuntimeError("Typst not installed. Install with: brew install typst")
        
        # Build invoice object
        customer = Customer(
            name=customer_name,
            address=customer_address,
            city=customer_city,
            country=customer_country,
            vat_id=customer_vat_id,
            reg_nr=customer_reg_nr,
        )
        
        items = [
            InvoiceItem(desc, qty, unit, price)
            for desc, qty, unit, price in line_items
        ]
        
        invoice = Invoice(
            invoice_nr=invoice_nr,
            invoice_date=invoice_date or datetime.now(),
            customer=customer,
            line_items=items,
            project_nr=project_nr,
        )
        
        # Generate Typst content
        typst_content = self._generate_typst_content(invoice, template)
        
        # Write temp file
        date_str = invoice.invoice_date.strftime("%Y-%m-%d")
        base_name = f"{date_str}_Invoice_{invoice_nr}"
        typst_file = self.output_dir / f"{base_name}.typ"
        pdf_file = self.output_dir / f"{base_name}.pdf"
        
        typst_file.write_text(typst_content)
        
        # Compile with Typst
        result = subprocess.run(
            ["typst", "compile", str(typst_file), str(pdf_file)],
            capture_output=True,
            text=True,
            cwd=self.templates_dir,  # So it finds fonts and logo
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Typst compilation failed: {result.stderr}")
        
        print(f"✅ Invoice generated: {pdf_file}")
        return pdf_file
    
    def list_invoices(self) -> List[Path]:
        """List all generated invoices."""
        return sorted(self.output_dir.glob("*.pdf"))


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate invoices")
    parser.add_argument("--list", action="store_true", help="List generated invoices")
    parser.add_argument("--new", action="store_true", help="Create new invoice (interactive)")
    
    args = parser.parse_args()
    
    svc = InvoiceService()
    
    if args.list:
        invoices = svc.list_invoices()
        print(f"📄 {len(invoices)} invoices:")
        for inv in invoices:
            print(f"   {inv.name}")
    
    elif args.new:
        print("🧾 New Invoice (interactive mode)")
        print("=" * 50)
        # TODO: Interactive prompts
        print("Not implemented yet - use Python API")
    
    else:
        parser.print_help()
