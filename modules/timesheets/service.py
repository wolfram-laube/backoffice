#!/usr/bin/env python3
"""
TIMESHEET SERVICE
=================
Parses YAML timesheets and generates invoices + service reports.
"""

import yaml
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def parse_timesheet(yaml_path: Path) -> Dict[str, Any]:
    """Parse a YAML timesheet file."""
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    entries = data.get('entries', [])
    rate = data.get('rate', 105.00)
    
    # Group by description for invoice line items
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
        'period': data.get('period', ''),
        'rate': rate,
        'entries': entries,
        'total_hours': sum(e.get('hours', 0) for e in entries),
        'line_items': [(desc, hours, 'hrs', r) for (desc, r), hours in line_items.items()],
    }


def generate_service_report(
    ts_data: Dict[str, Any],
    output_dir: Path,
    report_nr: str,
    templates_dir: Path = None,
) -> Path:
    """Generate a service report PDF from timesheet data."""
    
    if templates_dir is None:
        templates_dir = Path(__file__).parent.parent / 'invoicing' / 'templates'
    
    template_path = templates_dir / 'timesheet-report.typ'
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    template = template_path.read_text()
    customer = ts_data['customer']
    rate = ts_data['rate']
    
    # Format entries
    entries_typst = ",\n  ".join([
        f'("{e["date"]}", {e["hours"]}, "{e["description"]}")'
        for e in ts_data['entries']
    ])
    
    # Replace variables
    replacements = {
        'report_nr': f'"{report_nr}"',
        'report_date': f'"{datetime.now().strftime("%B %d, %Y")}"',
        'period': f'"{ts_data.get("period", "")}"',
        'project_nr': f'"{ts_data["project_nr"]}"',
        'customer_name': f'"{customer["name"]}"',
        'customer_address': f'"{customer["address"]}"',
        'customer_city': f'"{customer["city"]}"',
        'customer_country': f'"{customer["country"]}"',
    }
    
    content = template
    for key, value in replacements.items():
        pattern = rf'#let {key} = "[^"]*"'
        content = re.sub(pattern, f'#let {key} = {value}', content)
    
    content = re.sub(r'#let hourly_rate = [\d.]+', f'#let hourly_rate = {rate}', content)
    content = re.sub(
        r'#let entries = \([\s\S]*?\n\)',
        f'#let entries = (\n  {entries_typst},\n)',
        content
    )
    
    # Write and compile
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    typ_file = output_dir / f'{date_str}_ServiceReport_{report_nr}.typ'
    pdf_file = output_dir / f'{date_str}_ServiceReport_{report_nr}.pdf'
    
    typ_file.write_text(content)
    
    # Copy logo
    logo = templates_dir / 'logo-blauweiss.png'
    if logo.exists():
        shutil.copy(logo, output_dir / 'logo-blauweiss.png')
    
    # Compile
    fonts_dir = templates_dir.parent / 'fonts'
    result = subprocess.run(
        ['typst', 'compile', '--font-path', str(fonts_dir), str(typ_file), str(pdf_file)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Typst compilation failed: {result.stderr}")
    
    print(f"✅ Service Report: {pdf_file}")
    return pdf_file


def timesheet_to_invoice_package(
    yaml_path: Path,
    output_dir: Path = None,
    invoice_nr: str = None,
) -> Tuple[Path, Path]:
    """
    Generate complete invoice package from timesheet:
    - Invoice PDF
    - Service Report PDF (attachment)
    
    Returns:
        Tuple of (invoice_pdf, service_report_pdf)
    """
    from modules.invoicing.service import InvoiceService
    
    ts = parse_timesheet(yaml_path)
    customer = ts['customer']
    
    # Auto-generate numbers
    if not invoice_nr:
        date_str = datetime.now().strftime('%Y%m')
        customer_short = customer.get('name', 'XX')[:3].upper()
        invoice_nr = f"{customer_short}_{date_str}_001"
    
    report_nr = invoice_nr.replace('_', '-')
    
    if output_dir is None:
        output_dir = yaml_path.parent / 'output'
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate Invoice
    svc = InvoiceService()
    svc.output_dir = output_dir
    
    invoice_pdf = svc.create_invoice(
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
    
    # Generate Service Report
    report_pdf = generate_service_report(
        ts,
        output_dir,
        report_nr,
        templates_dir=Path(__file__).parent.parent / 'invoicing' / 'templates'
    )
    
    return invoice_pdf, report_pdf


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate invoice package from timesheet')
    parser.add_argument('timesheet', help='Path to timesheet YAML file')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-n', '--invoice-nr', help='Invoice number')
    
    args = parser.parse_args()
    
    invoice_pdf, report_pdf = timesheet_to_invoice_package(
        Path(args.timesheet),
        Path(args.output) if args.output else None,
        args.invoice_nr
    )
    
    print(f"")
    print(f"📦 Invoice Package Generated:")
    print(f"   📄 Invoice: {invoice_pdf}")
    print(f"   📋 Service Report: {report_pdf}")
