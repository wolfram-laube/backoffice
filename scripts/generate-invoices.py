#!/usr/bin/env python3
"""
Generate invoices from timesheets.
Triggered by CI/CD pipeline when timesheets/*.yaml changes.
"""

import os
import sys
import yaml
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Paths
ROOT = Path(__file__).parent.parent
TIMESHEETS_DIR = ROOT / "timesheets"
INVOICES_DIR = ROOT / "invoices"
MODULES_DIR = ROOT / "modules"

sys.path.insert(0, str(ROOT))


def find_changed_timesheets():
    """Find timesheets changed in the last commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True
        )
        files = result.stdout.strip().split('\n')
        return [f for f in files if f.startswith('timesheets/') and f.endswith(('.yaml', '.yml'))]
    except:
        # Fallback: process all timesheets
        return [str(p.relative_to(ROOT)) for p in TIMESHEETS_DIR.glob('*.yaml')]


def parse_timesheet(yaml_path):
    """Parse a YAML timesheet."""
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    entries = data.get('entries', [])
    rate = data.get('rate', 105.00)
    
    # Group by description
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
        'line_items': [(desc, hours, 'hrs', r) for (desc, r), hours in line_items.items()],
    }


def generate_invoice(timesheet_path):
    """Generate invoice from timesheet."""
    from modules.invoicing.service import InvoiceService
    
    ts = parse_timesheet(timesheet_path)
    customer = ts['customer']
    
    # Invoice number from filename
    filename = Path(timesheet_path).stem  # e.g., "2026-01-krongaard"
    date_str = datetime.now().strftime('%Y%m')
    invoice_nr = f"{filename.upper().replace('-', '_')}_{date_str}"
    
    # Ensure invoices dir exists
    INVOICES_DIR.mkdir(exist_ok=True)
    
    # Copy logo to invoices dir
    logo_src = MODULES_DIR / "invoicing" / "templates" / "logo-blauweiss.png"
    if logo_src.exists():
        shutil.copy(logo_src, INVOICES_DIR / "logo-blauweiss.png")
    
    svc = InvoiceService(output_dir=INVOICES_DIR)
    
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


def main():
    print("🧾 Invoice Generator")
    print("=" * 50)
    
    timesheets = find_changed_timesheets()
    
    if not timesheets:
        print("No changed timesheets found.")
        # Generate all anyway for manual runs
        timesheets = [str(p.relative_to(ROOT)) for p in TIMESHEETS_DIR.glob('*.yaml')]
    
    print(f"Found {len(timesheets)} timesheet(s)")
    
    generated = []
    for ts_path in timesheets:
        full_path = ROOT / ts_path
        if not full_path.exists():
            print(f"  ⚠️ {ts_path} not found, skipping")
            continue
            
        print(f"  📄 {ts_path}")
        try:
            pdf = generate_invoice(full_path)
            print(f"     ✅ {pdf.name}")
            generated.append(pdf)
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    print()
    print(f"Generated {len(generated)} invoice(s)")
    
    # List all invoices
    print("\n📁 invoices/")
    for pdf in INVOICES_DIR.glob('*.pdf'):
        print(f"   {pdf.name}")


if __name__ == '__main__':
    main()
