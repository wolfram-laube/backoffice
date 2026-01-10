#!/usr/bin/env python3
"""Generate invoice packages from timesheets."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from modules.timesheets.service import timesheet_to_invoice_package

def main():
    timesheets_dir = Path('timesheets')
    output_dir = Path('invoices')
    output_dir.mkdir(exist_ok=True)
    
    # Find all timesheets
    yaml_files = list(timesheets_dir.glob('*.yaml')) + list(timesheets_dir.glob('*.yml'))
    
    if not yaml_files:
        print("No timesheets found")
        return
    
    for ts_file in yaml_files:
        print(f"📄 Processing: {ts_file}")
        try:
            invoice, report = timesheet_to_invoice_package(ts_file, output_dir)
            print(f"   ✅ Invoice: {invoice.name}")
            print(f"   ✅ Report: {report.name}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    main()
