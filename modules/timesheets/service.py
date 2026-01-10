#!/usr/bin/env python3
"""
TIMESHEET SERVICE
=================
Parses YAML timesheets and generates invoices.
"""

import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import sys

# Add parent for invoicing import
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_timesheet(yaml_path: Path) -> Dict[str, Any]:
    """Parse a YAML timesheet file."""
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Calculate totals
    entries = data.get('entries', [])
    total_hours = sum(e.get('hours', 0) for e in entries)
    rate = data.get('rate', 105.00)
    
    # Group by description for line items
    line_items = {}
    for entry in entries:
        desc = entry.get('description', 'Consulting')
        hours = entry.get('hours', 0)
        entry_rate = entry.get('rate', rate)
        
        key = (desc, entry_rate)
        if key in line_items:
            line_items[key] += hours
        else:
            line_items[key] = hours
    
    return {
        'customer': data.get('customer', {}),
        'project_nr': data.get('project_nr', ''),
        'rate': rate,
        'entries': entries,
        'total_hours': total_hours,
        'line_items': [(desc, hours, 'hrs', r) for (desc, r), hours in line_items.items()],
        'period': data.get('period', ''),
    }


def timesheet_to_invoice(
    yaml_path: Path,
    output_dir: Path = None,
    invoice_nr: str = None,
) -> Path:
    """
    Generate an invoice from a timesheet YAML file.
    
    Args:
        yaml_path: Path to timesheet YAML
        output_dir: Where to save the invoice (default: same as yaml)
        invoice_nr: Invoice number (default: auto-generate)
    
    Returns:
        Path to generated PDF
    """
    from modules.invoicing.service import InvoiceService
    
    # Parse timesheet
    ts = parse_timesheet(yaml_path)
    customer = ts['customer']
    
    # Auto-generate invoice number if not provided
    if not invoice_nr:
        date_str = datetime.now().strftime('%Y%m')
        customer_short = customer.get('name', 'XX')[:3].upper()
        invoice_nr = f"{customer_short}_{date_str}_001"
    
    # Create invoice
    svc = InvoiceService()
    
    if output_dir:
        svc.output_dir = Path(output_dir)
        svc.output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf = svc.create_invoice(
        invoice_nr=invoice_nr,
        customer_name=customer.get('name', ''),
        customer_address=customer.get('address', ''),
        customer_city=customer.get('city', ''),
        customer_country=customer.get('country', ''),
        customer_vat_id=customer.get('vat_id', ''),
        customer_reg_nr=customer.get('reg_nr', ''),
        line_items=ts['line_items'],
        project_nr=ts.get('project_nr', ''),
        template='en-eu'
    )
    
    return pdf


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate invoice from timesheet')
    parser.add_argument('timesheet', help='Path to timesheet YAML file')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-n', '--invoice-nr', help='Invoice number')
    
    args = parser.parse_args()
    
    pdf = timesheet_to_invoice(
        Path(args.timesheet),
        Path(args.output) if args.output else None,
        args.invoice_nr
    )
    
    print(f"✅ Invoice generated: {pdf}")
