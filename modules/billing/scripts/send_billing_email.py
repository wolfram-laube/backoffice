#!/usr/bin/env python3
"""
Gmail Billing Draft Creator with PDF Attachments.

Creates a draft email with invoice and timesheets attached.

Environment Variables:
  - GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN: Gmail OAuth
  - BILLING_CLIENT: Client ID (e.g., "nemensis")
  - BILLING_PERIOD: Period (e.g., "2026-01")
"""
import os
import json
import base64
import glob
import yaml
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path


def get_access_token():
    """Get OAuth access token from refresh token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["GMAIL_CLIENT_ID"],
            "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
            "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
            "grant_type": "refresh_token"
        }
    )
    if response.status_code != 200:
        raise Exception(f"Token error: {response.text}")
    return response.json()["access_token"]


def create_draft(access_token: str, raw_message: str) -> dict:
    """Create a Gmail draft."""
    raw_b64 = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")
    
    response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={"message": {"raw": raw_b64}}
    )
    
    if response.status_code not in (200, 201):
        raise Exception(f"Draft creation failed: {response.text}")
    
    return response.json()


def load_client_config(client_id: str) -> dict:
    """Load client configuration from clients.yaml."""
    config_path = Path("billing/config/clients.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    if client_id not in config.get("clients", {}):
        raise ValueError(f"Client not found: {client_id}")
    
    return config["clients"][client_id], config.get("consultants", {})


def find_billing_files(client_id: str, period: str) -> tuple[list, str]:
    """Find timesheet and invoice PDFs for the given client/period."""
    output_dir = Path("billing/output")
    
    # Find timesheets: {period}_timesheet_{client}_*.pdf
    timesheets = list(output_dir.glob(f"*_{client_id}_{period}_timesheet.pdf"))
    
    # Find latest invoice: AR_*_{client}.pdf
    invoices = sorted(output_dir.glob(f"{client_id}_{period}_invoice_AR_*.pdf"), reverse=True)
    invoice = invoices[0] if invoices else None
    
    return timesheets, invoice


def parse_sync_files(client_id: str, period: str) -> list[dict]:
    """Parse sync.json files to get hours breakdown."""
    output_dir = Path("billing/output")
    sync_files = output_dir.glob(f"*_{client_id}_{period}_timesheet.sync.json")
    
    breakdown = []
    for sf in sync_files:
        with open(sf) as f:
            data = json.load(f)
            breakdown.append({
                "consultant_id": data.get("consultant_id"),
                "hours": data.get("total_hours", 0)
            })
    
    return breakdown


def build_email(
    client_config: dict,
    consultants: dict,
    period: str,
    timesheets: list,
    invoice: Path,
    breakdown: list[dict]
) -> MIMEMultipart:
    """Build the email with attachments."""
    
    # Email recipient from client config
    to_email = client_config.get("billing_email", client_config.get("email", ""))
    client_name = client_config.get("name", "")
    rate = client_config.get("rates", {}).get("remote", 0)
    
    # Calculate totals
    total_hours = sum(b["hours"] for b in breakdown)
    total_amount = total_hours * rate
    
    # Build hours breakdown text
    hours_lines = []
    for b in breakdown:
        consultant_name = consultants.get(b["consultant_id"], {}).get("name", b["consultant_id"])
        hours_lines.append(f"  • {consultant_name}: {b['hours']:.1f}h")
    hours_text = "\n".join(hours_lines)
    
    # Invoice number from filename
    invoice_number = invoice.stem if invoice else "N/A"
    
    # Build email body
    body = f"""Sehr geehrte Damen und Herren,

anbei übersende ich Ihnen unsere Rechnung für die im {period} erbrachten Beratungsleistungen.

Leistungsübersicht:
{hours_text}

Gesamt: {total_hours:.1f} Stunden × EUR {rate:.2f} = EUR {total_amount:,.2f} netto

Anlagen:
  • Rechnung {invoice_number} (PDF)
{chr(10).join(f"  • Leistungsnachweis {consultants.get(b['consultant_id'], {}).get('name', b['consultant_id'])} (PDF)" for b in breakdown)}

Bei Rückfragen stehe ich Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen

Wolfram Laube
BLAUWEISS EDV LLC
wolfram.laube@blauweiss-edv.at
"""

    # Create MIME message
    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["Subject"] = f"Rechnung {invoice_number} - BLAUWEISS EDV LLC - {period}"
    msg["From"] = "wolfram.laube@blauweiss-edv.at"
    
    # Add body
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    # Add invoice PDF
    if invoice and invoice.exists():
        with open(invoice, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header("Content-Disposition", "attachment", filename=invoice.name)
            msg.attach(attachment)
            print(f"  📎 Attached: {invoice.name}")
    
    # Add timesheet PDFs
    for ts in timesheets:
        if ts.exists():
            with open(ts, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header("Content-Disposition", "attachment", filename=ts.name)
                msg.attach(attachment)
                print(f"  📎 Attached: {ts.name}")
    
    return msg


def main():
    client_id = os.environ.get("BILLING_CLIENT", "")
    period = os.environ.get("BILLING_PERIOD", "")
    
    if not client_id or not period:
        print("❌ BILLING_CLIENT and BILLING_PERIOD must be set")
        return 1
    
    print(f"📧 Creating billing draft for {client_id} - {period}")
    
    # Load configuration
    client_config, consultants = load_client_config(client_id)
    print(f"  Client: {client_config.get('name')}")
    
    # Find files
    timesheets, invoice = find_billing_files(client_id, period)
    print(f"  Found: {len(timesheets)} timesheet(s), invoice: {invoice.name if invoice else 'None'}")
    
    if not invoice:
        print("❌ No invoice found!")
        return 1
    
    # Get hours breakdown
    breakdown = parse_sync_files(client_id, period)
    print(f"  Breakdown: {breakdown}")
    
    # Build email
    msg = build_email(client_config, consultants, period, timesheets, invoice, breakdown)
    
    # Get access token
    print("  🔑 Getting OAuth token...")
    access_token = get_access_token()
    
    # Create draft
    print("  📝 Creating draft...")
    result = create_draft(access_token, msg.as_string())
    
    draft_id = result.get("id", "unknown")
    print(f"✅ Draft created! ID: {draft_id}")
    print(f"   → Check your Gmail Drafts folder")
    
    return 0


if __name__ == "__main__":
    exit(main())
