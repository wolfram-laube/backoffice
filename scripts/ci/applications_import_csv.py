#!/usr/bin/env python3
"""Import bewerbungen CSV into SQLite database.

Handles known data quality issues:
  - Column shift: some rows have workload in rate_eur_h and rate in status
  - Rate ranges: "100-110" → take first value (100.0)
  - Non-numeric rates: "nicht angegeben", "100% Vollzeit" → None
  - Match score extraction: "MATCH 85%!" in notes → 85

Usage:
    python scripts/ci/applications_import_csv.py [--csv PATH] [--db PATH] [--dry-run]
"""
import argparse
import csv
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.models import Application, Base
from modules.applications.database import get_engine, get_session, get_db_path

logger = logging.getLogger(__name__)

# Default CSV path (in repo root or CI artifact)
DEFAULT_CSV = "bewerbungen_komplett_SORTED_Jan_31_2026.csv"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_rate(raw: str) -> Optional[float]:
    """Parse rate_eur_h from various formats.

    "105"        → 105.0
    "100-110"    → 100.0  (take lower bound)
    "95-105"     → 95.0
    "100% Vollzeit" → None  (this is workload, not rate)
    "nicht angegeben" → None
    "?"          → None
    ""           → None
    """
    if not raw or not raw.strip():
        return None

    raw = raw.strip()

    # Direct numeric
    try:
        return float(raw)
    except ValueError:
        pass

    # Range: "100-110" → take lower bound
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)$", raw)
    if m:
        return float(m.group(1))

    # Any leading number
    m = re.match(r"^(\d+(?:\.\d+)?)", raw)
    if m and raw[len(m.group(0)):].strip().startswith(("€", "EUR")):
        return float(m.group(1))

    # Not a rate
    return None


def parse_match_score(notes: str) -> Optional[int]:
    """Extract match score from notes field.

    "MATCH 85%!" → 85
    "Match 90%+! ENDKUNDE..." → 90
    "GULP Alert, 50Hertz-Match 90%+, KRITIS" → 90
    """
    if not notes:
        return None

    m = re.search(r"MATCH\s+(\d+)%", notes, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def parse_date(raw: str) -> Optional[date]:
    """Parse date from YYYY-MM-DD format."""
    if not raw or not raw.strip():
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"Unparseable date: '{raw}'")
        return None


def detect_column_shift(row: dict) -> Tuple[Optional[float], str, str]:
    """Detect and fix column shift where workload→rate and rate→status.

    Returns: (rate, status, workload)

    Known pattern: when rate_eur_h contains workload text ("100% Vollzeit")
    and status contains a number ("105"), the columns are shifted.
    """
    raw_rate = row.get("rate_eur_h", "").strip()
    raw_status = row.get("status", "").strip()
    raw_workload = row.get("workload", "").strip()

    # Check if status looks like a rate (pure number)
    # and rate_eur_h looks like workload text OR is empty
    status_is_numeric = False
    try:
        float(raw_status)
        status_is_numeric = True
    except (ValueError, TypeError):
        pass

    rate_is_text = raw_rate and parse_rate(raw_rate) is None
    rate_is_empty = not raw_rate

    if status_is_numeric and (rate_is_text or rate_is_empty):
        # Column shift detected!
        actual_rate = float(raw_status)
        actual_status = row.get("notes", "").strip()  # notes has real status
        actual_workload = raw_rate if raw_rate else raw_workload  # rate field has workload (or empty)

        logger.debug(
            f"Column shift detected: "
            f"rate={raw_rate}→workload, status={raw_status}→rate={actual_rate}"
        )
        return actual_rate, actual_status, actual_workload

    # Normal parsing
    rate = parse_rate(raw_rate)
    return rate, raw_status, raw_workload


def csv_row_to_application(row: dict, row_num: int) -> Application:
    """Convert one CSV row to an Application model instance."""
    rate, status, workload = detect_column_shift(row)
    match_score = parse_match_score(row.get("notes", ""))
    date_recorded = parse_date(row.get("date_recorded", ""))

    return Application(
        date_recorded=date_recorded,
        project_title=row.get("project_title", "").strip(),
        provider=row.get("provider", "").strip() or None,
        contact_name=row.get("contact_name", "").strip() or None,
        contact_email=row.get("contact_email", "").strip() or None,
        phone=row.get("phone", "").strip() or None,
        location=row.get("location", "").strip() or None,
        start_date=row.get("start", "").strip() or None,
        duration=row.get("duration", "").strip() or None,
        workload=workload or None,
        rate_eur_h=rate,
        status=status or None,
        match_score=match_score,
        notes=row.get("notes", "").strip() or None,
        source_url=None,  # Not in CSV
        project_id=None,  # Not in CSV
    )


# ---------------------------------------------------------------------------
# Main import
# ---------------------------------------------------------------------------

def import_csv(csv_path: Path, db_path: Optional[Path] = None, dry_run: bool = False) -> int:
    """Import CSV into SQLite database.

    Returns number of imported rows.
    """
    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return 0

    # Read CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info(f"Read {len(rows)} rows from {csv_path}")

    if dry_run:
        # Just validate
        errors = 0
        for i, row in enumerate(rows, start=2):
            try:
                app = csv_row_to_application(row, i)
                if not app.project_title:
                    logger.warning(f"Row {i}: empty project_title")
                    errors += 1
            except Exception as e:
                logger.error(f"Row {i}: {e}")
                errors += 1
        logger.info(f"Dry run complete: {len(rows)} rows, {errors} errors")
        return len(rows) - errors

    # Create DB and import
    db_path = db_path or get_db_path()
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import Session

    imported = 0
    with Session(engine) as session:
        for i, row in enumerate(rows, start=2):
            try:
                app = csv_row_to_application(row, i)
                session.add(app)
                imported += 1
            except Exception as e:
                logger.error(f"Row {i}: failed to import — {e}")
                continue

        session.commit()

    engine.dispose()
    logger.info(f"Imported {imported}/{len(rows)} rows into {db_path}")
    return imported


def main():
    parser = argparse.ArgumentParser(description="Import bewerbungen CSV into SQLite")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(DEFAULT_CSV),
        help=f"Path to CSV file (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite database (default: from APPTRACK_DB_PATH or /tmp/applications.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate CSV without writing to DB",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.db:
        import os
        os.environ["APPTRACK_DB_PATH"] = str(args.db)

    count = import_csv(args.csv, args.db, args.dry_run)

    if count == 0:
        logger.error("No rows imported!")
        sys.exit(1)

    logger.info(f"✓ {count} applications imported successfully")


if __name__ == "__main__":
    main()
