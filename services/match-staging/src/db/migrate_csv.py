"""Migrate CSV bewerbungen data to SQLite database.

Handles:
- Status normalization (50+ variants → 12 clean enum values)
- Date extraction from status strings
- Rate field cleanup (some rows have rate in status field)
- Audit trail creation for initial import

Usage:
    python -m src.db.migrate_csv path/to/bewerbungen.csv [--db sqlite:///data/bewerbungen.db]
"""

import asyncio
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select, func

from src.db.connection import init_db, get_session, get_engine
from src.db.models import Application, ApplicationStatus, StatusHistory


# --- Status Normalization Map ---

STATUS_MAP: dict[str, ApplicationStatus] = {
    # Direct mappings
    "versendet": ApplicationStatus.SENT,
    "abgelehnt": ApplicationStatus.REJECTED,
    "absage": ApplicationStatus.REJECTED,
    "nicht beworben": ApplicationStatus.NOT_APPLIED,
    "vorbereitet": ApplicationStatus.IDENTIFIED,
    "neu identifiziert": ApplicationStatus.IDENTIFIED,
    "keine rueckmeldung": ApplicationStatus.NO_RESPONSE,

    # Compound status patterns
    "versendet via freelancermap": ApplicationStatus.SENT,
    "versendet beim kunden": ApplicationStatus.AT_CLIENT,
    "vorgestellt beim kunden": ApplicationStatus.AT_CLIENT,
    "wird beim kunden vorgestellt": ApplicationStatus.AT_CLIENT,
    "in verhandlung": ApplicationStatus.IN_NEGOTIATION,
    "vertrag erhalten": ApplicationStatus.CONTRACT,
    "position bereits besetzt": ApplicationStatus.REJECTED,
    "selbsteinschätzung versendet": ApplicationStatus.SENT,
}

# Patterns for regex matching
STATUS_PATTERNS = [
    (r"^absage", ApplicationStatus.REJECTED),
    (r"^abgelehnt", ApplicationStatus.REJECTED),
    (r"^versendet", ApplicationStatus.SENT),
    (r"kunde.*profil.*spannend|interview", ApplicationStatus.INTERVIEW),
    (r"beim kunden", ApplicationStatus.AT_CLIENT),
    (r"telefonat", ApplicationStatus.INTERVIEW),
    (r"verhandlung", ApplicationStatus.IN_NEGOTIATION),
    (r"vertrag", ApplicationStatus.CONTRACT),
]

# Date extraction pattern
DATE_PATTERN = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
ISO_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")


def normalize_status(raw_status: str) -> tuple[ApplicationStatus, Optional[date], str]:
    """Normalize messy status strings to clean enum + date + detail.

    Returns:
        (status_enum, status_date, status_detail)
    """
    raw = raw_status.strip()
    raw_lower = raw.lower()

    # Extract date if present
    status_date = None
    date_match = DATE_PATTERN.search(raw)
    if date_match:
        try:
            status_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        except ValueError:
            pass

    # Check if it's just a number (rate in wrong field)
    if raw.isdigit():
        return ApplicationStatus.SENT, None, f"rate_in_status_field: {raw}"

    # Try direct mapping first
    for key, status in STATUS_MAP.items():
        if raw_lower.startswith(key) or raw_lower == key:
            return status, status_date, raw

    # Try regex patterns
    for pattern, status in STATUS_PATTERNS:
        if re.search(pattern, raw_lower):
            return status, status_date, raw

    # Fallback: if contains "versendet", it's sent
    if "versendet" in raw_lower or "gesendet" in raw_lower:
        return ApplicationStatus.SENT, status_date, raw

    # Unknown — keep original as detail, mark as sent (most common)
    return ApplicationStatus.SENT, status_date, f"unmapped: {raw}"


def parse_date(date_str: str) -> Optional[date]:
    """Parse date from various formats."""
    if not date_str or date_str.strip() in ("—", "-", ""):
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def parse_rate(rate_str: str) -> Optional[int]:
    """Extract numeric rate from string."""
    if not rate_str:
        return None
    # Remove common suffixes
    clean = re.sub(r"[^\d]", "", rate_str.strip())
    if clean and clean.isdigit():
        val = int(clean)
        return val if 50 <= val <= 300 else None  # Sanity check
    return None


def detect_platform(notes: str, provider: str) -> str:
    """Detect source platform from notes and provider."""
    combined = f"{notes} {provider}".lower()
    if "freelancermap" in combined:
        return "freelancermap"
    elif "gulp" in combined:
        return "gulp"
    elif "randstad" in combined:
        return "randstad"
    elif "hays" in combined:
        return "hays"
    elif "xing" in combined:
        return "xing"
    elif "linkedin" in combined:
        return "linkedin"
    return "other"


async def migrate_csv(csv_path: str, dry_run: bool = False) -> dict:
    """Migrate CSV to database.

    Args:
        csv_path: Path to the bewerbungen CSV
        dry_run: If True, only analyze without writing

    Returns:
        Migration statistics
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # Read CSV
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    stats = {
        "total_rows": len(rows),
        "imported": 0,
        "skipped": 0,
        "status_mappings": {},
        "errors": [],
    }

    if not dry_run:
        await init_db()

    applications = []
    for i, row in enumerate(rows):
        try:
            # Clean up row (handle extra columns from CSV messiness)
            row = {k: (v.strip() if v else "") for k, v in row.items() if k}

            # Parse fields
            date_recorded = parse_date(row.get("date_recorded", ""))
            if not date_recorded:
                stats["errors"].append(f"Row {i}: No date_recorded")
                stats["skipped"] += 1
                continue

            # Normalize status
            raw_status = row.get("status", "")
            status, status_date, status_detail = normalize_status(raw_status)

            # Track status mapping for reporting
            key = f"{raw_status[:50]} → {status.value}"
            stats["status_mappings"][key] = stats["status_mappings"].get(key, 0) + 1

            # Handle rate-in-status-field issue
            rate = parse_rate(row.get("rate_eur_h", ""))
            if rate is None and raw_status.isdigit():
                rate = int(raw_status) if 50 <= int(raw_status) <= 300 else 105

            app = Application(
                date_recorded=date_recorded,
                project_title=row.get("project_title", "Unknown"),
                provider=row.get("provider", "Unknown"),
                contact_name=row.get("contact_name", "") or None,
                contact_email=row.get("contact_email", "") or None,
                phone=row.get("phone", "") or None,
                location=row.get("location", "") or None,
                start_date=row.get("start", "") or None,
                duration=row.get("duration", "") or None,
                workload=row.get("workload", "") or None,
                rate_eur_h=rate or 105,
                source_platform=detect_platform(
                    row.get("notes", ""), row.get("provider", "")
                ),
                status=status.value,
                status_date=status_date or date_recorded,
                status_detail=status_detail if status_detail != raw_status else None,
                notes=row.get("notes", "") or None,
            )
            applications.append(app)
            stats["imported"] += 1

        except Exception as e:
            stats["errors"].append(f"Row {i}: {e}")
            stats["skipped"] += 1

    if dry_run:
        return stats

    # Write to database
    async with get_session() as session:
        session.add_all(applications)
        await session.flush()

        # Create initial status history entries
        for app in applications:
            history = StatusHistory(
                application_id=app.id,
                old_status=None,
                new_status=app.status,
                comment=f"Imported from CSV (original: {app.status_detail or app.status})",
                changed_by="csv_migration",
            )
            session.add(history)

    # Verify
    async with get_session() as session:
        count = await session.scalar(select(func.count(Application.id)))
        stats["db_count"] = count

    return stats


async def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.db.migrate_csv <csv_path> [--dry-run]")
        sys.exit(1)

    csv_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    print(f"{'DRY RUN — ' if dry_run else ''}Migrating: {csv_path}")
    print("=" * 60)

    stats = await migrate_csv(csv_path, dry_run=dry_run)

    print(f"\nTotal rows:  {stats['total_rows']}")
    print(f"Imported:    {stats['imported']}")
    print(f"Skipped:     {stats['skipped']}")
    if not dry_run:
        print(f"DB count:    {stats.get('db_count', 'N/A')}")

    print(f"\n--- Status Mappings ---")
    for mapping, count in sorted(stats["status_mappings"].items(), key=lambda x: -x[1]):
        print(f"  {count:3d}x  {mapping}")

    if stats["errors"]:
        print(f"\n--- Errors ({len(stats['errors'])}) ---")
        for err in stats["errors"][:10]:
            print(f"  ⚠️  {err}")

    if not dry_run:
        print(f"\n✅ Migration complete. Database: data/bewerbungen.db")


if __name__ == "__main__":
    asyncio.run(main())
