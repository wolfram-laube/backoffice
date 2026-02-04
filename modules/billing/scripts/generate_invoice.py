#!/usr/bin/env python3
"""
CLARISSA Invoice Generator

Generates consolidated invoices from timesheet data.

Usage:
    # From all timesheets for a client/period
    python generate_invoice.py --client nemensis --period 2026-01
    
    # Or from specific timesheets
    python generate_invoice.py --from-timesheets 2026-01_timesheet_nemensis_*.typ
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

try:
    import yaml
except ImportError:
    print("❌ Missing dependency: pyyaml")
    print("   pip install pyyaml")
    sys.exit(1)

# Paths
SCRIPT_DIR = Path(__file__).parent
BILLING_DIR = SCRIPT_DIR.parent
CONFIG_DIR = BILLING_DIR / "config"
TEMPLATES_DIR = BILLING_DIR / "templates"
OUTPUT_DIR = BILLING_DIR / "output"


def load_config() -> dict:
    """Load client configuration."""
    config_file = CONFIG_DIR / "clients.yaml"
    if not config_file.exists():
        print(f"❌ Config not found: {config_file}")
        sys.exit(1)
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_sequences() -> dict:
    """Load invoice number sequences."""
    seq_file = CONFIG_DIR / "sequences.yaml"
    if seq_file.exists():
        with open(seq_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_sequences(sequences: dict):
    """Save invoice number sequences."""
    seq_file = CONFIG_DIR / "sequences.yaml"
    seq_file.parent.mkdir(parents=True, exist_ok=True)
    with open(seq_file, "w", encoding="utf-8") as f:
        yaml.dump(sequences, f, default_flow_style=False)


def get_next_invoice_number(year: int, sequences: dict) -> int:
    """Get and increment the next invoice number for a year."""
    key = f"invoice_{year}"
    current = sequences.get(key, 0)
    sequences[key] = current + 1
    return current + 1


def find_timesheets(client_id: str, year: int, month: int) -> List[Path]:
    """Find all timesheets for a client/period."""
    pattern = f"*_{client_id}_{year}-{month:02d}_timesheet.sync.json"
    sync_files = list(OUTPUT_DIR.glob(pattern))
    return sync_files


def load_timesheet_data(sync_files: List[Path]) -> Dict:
    """Load and aggregate timesheet data from sync files."""
    aggregated = {
        "consultants": [],
        "total_hours": 0,
        "entries_by_consultant": {}
    }
    
    for sync_file in sync_files:
        with open(sync_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        consultant_id = data.get("consultant_id")
        hours = data.get("total_hours", 0)
        
        aggregated["consultants"].append(consultant_id)
        aggregated["total_hours"] += hours
        aggregated["entries_by_consultant"][consultant_id] = {
            "hours": hours,
            "entries": data.get("entries", {})
        }
    
    return aggregated


def generate_invoice_typ(
    invoice_number: str,
    year: int,
    month: int,
    client_id: str,
    client_config: dict,
    timesheet_data: dict,
    config: dict
) -> str:
    """Generate Typst invoice content."""
    
    # Get rates
    rates = client_config.get("rates", {})
    remote_rate = rates.get("remote", 100)
    onsite_rate = rates.get("onsite", 120)
    
    # For now, assume all hours are remote
    total_hours = timesheet_data["total_hours"]
    
    # Format invoice date
    invoice_date = datetime.now()
    date_formats = {
        "rechnung-de": f"{invoice_date.day:02d}. {['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'][invoice_date.month-1]} {invoice_date.year}",
        "invoice-en-us": invoice_date.strftime("%B %d, %Y"),
        "invoice-en-eu": invoice_date.strftime("%d %B %Y"),
    }
    template = client_config.get("template", "rechnung-de")
    formatted_date = date_formats.get(template, invoice_date.strftime("%Y-%m-%d"))
    
    # Build consultant breakdown comment
    breakdown_lines = []
    for consultant_id, data in timesheet_data["entries_by_consultant"].items():
        consultant_name = config.get("consultants", {}).get(consultant_id, {}).get("name", consultant_id)
        breakdown_lines.append(f"//   - {consultant_name}: {data['hours']:.1f}h")
    breakdown = "\n".join(breakdown_lines)
    
    # Get address
    address = client_config.get("address", {})
    
    content = f'''// BLAUWEISS Invoice - {invoice_number}
// Client: {client_config.get('name', '')}
// Period: {year}-{month:02d}
// Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
//
// Hours breakdown:
{breakdown}
// Total: {total_hours:.1f}h × EUR {remote_rate} = EUR {total_hours * remote_rate:,.2f}

#import "../templates/{template}.typ": invoice

#invoice(
  invoice_number: "{invoice_number}",
  invoice_date: "{formatted_date}",
  client_name: "{client_config.get('name', '')}",
  client_address: "{address.get('street', '')}",
  client_city: "{address.get('city', '')}",
  client_reg_id: "{client_config.get('reg_id', '')}",
  client_vat_id: "{client_config.get('vat_id', '')}",
  contract_number: "{client_config.get('contract_number', '')}",
  remote_hours: {total_hours},
  remote_rate: {remote_rate},
  onsite_hours: 0,
  onsite_rate: {onsite_rate},
)
'''
    return content


def main():
    parser = argparse.ArgumentParser(
        description="Generate consolidated invoices from timesheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # From all timesheets for client/period
    %(prog)s --client nemensis --period 2026-01
    
    # With custom invoice number
    %(prog)s --client nemensis --period 2026-01 --invoice-number AR_042_2026
    
Workflow:
    1. Generate timesheets: generate_timesheet.py --client X --period YYYY-MM --all-consultants
    2. Review and approve timesheets
    3. Generate invoice: generate_invoice.py --client X --period YYYY-MM
"""
    )
    parser.add_argument("--client", "-c", required=True, help="Client ID from clients.yaml")
    parser.add_argument("--period", "-p", required=True, help="Period as YYYY-MM")
    parser.add_argument("--invoice-number", help="Override invoice number (default: auto)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    
    args = parser.parse_args()
    
    # Parse period
    try:
        year, month = map(int, args.period.split("-"))
    except ValueError:
        print(f"❌ Invalid period format: {args.period}")
        print("   Use YYYY-MM (e.g., 2026-01)")
        sys.exit(1)
    
    # Load config
    config = load_config()
    
    # Validate client
    if args.client not in config.get("clients", {}):
        print(f"❌ Unknown client: {args.client}")
        available = [k for k in config.get("clients", {}).keys() if not k.startswith("_")]
        print(f"   Available: {', '.join(available)}")
        sys.exit(1)
    
    client_config = config["clients"][args.client]
    
    print(f"📋 Generating invoice:")
    print(f"   Client: {client_config['name']}")
    print(f"   Period: {year}-{month:02d}")
    
    # Find timesheets
    sync_files = find_timesheets(args.client, year, month)
    
    if not sync_files:
        print(f"\n❌ No timesheets found for {args.client} in {year}-{month:02d}")
        print(f"   Expected files matching: {year}-{month:02d}_timesheet_{args.client}_*.sync.json")
        print(f"\n   Generate timesheets first:")
        print(f"   python generate_timesheet.py --client {args.client} --period {args.period} --all-consultants")
        sys.exit(1)
    
    print(f"   Found {len(sync_files)} timesheet(s)")
    
    # Load timesheet data
    timesheet_data = load_timesheet_data(sync_files)
    
    # Show breakdown
    print(f"\n   Hours breakdown:")
    for consultant_id, data in timesheet_data["entries_by_consultant"].items():
        consultant_name = config.get("consultants", {}).get(consultant_id, {}).get("name", consultant_id)
        print(f"     - {consultant_name}: {data['hours']:.1f}h")
    
    total_hours = timesheet_data["total_hours"]
    rate = client_config.get("rates", {}).get("remote", 100)
    currency = client_config.get("currency", "EUR")
    total_amount = total_hours * rate
    
    print(f"\n   Total: {total_hours:.1f}h × {currency} {rate} = {currency} {total_amount:,.2f}")
    
    if args.dry_run:
        print("\n⚠️ Dry run - no invoice generated")
        return
    
    # Get invoice number
    sequences = load_sequences()
    if args.invoice_number:
        invoice_number = args.invoice_number
        # Extract seq_num from provided number if possible
        import re
        match = re.search(r'AR_(\d+)', invoice_number)
        seq_num = int(match.group(1)) if match else 1
    else:
        seq_num = get_next_invoice_number(year, sequences)
        invoice_number = f"AR_{seq_num:03d}_{year}"
        save_sequences(sequences)
    
    print(f"\n   Invoice number: {invoice_number}")
    
    # Generate invoice
    content = generate_invoice_typ(
        invoice_number, year, month,
        args.client, client_config,
        timesheet_data, config
    )
    
    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{args.client}_{year}-{month:02d}_invoice_AR_{seq_num:03d}.typ"
    output_file = OUTPUT_DIR / filename
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"\n✅ Generated: {output_file.name}")
    print(f"\nNext steps:")
    print(f"   1. Review the invoice")
    print(f"   2. Commit and push to trigger CI:")
    print(f"      git add billing/output/")
    print(f"      git commit -m 'billing: {args.client} {args.period}'")
    print(f"      git push")


if __name__ == "__main__":
    main()
