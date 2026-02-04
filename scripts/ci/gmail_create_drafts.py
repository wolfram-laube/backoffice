#!/usr/bin/env python3
"""
CI Script: Gmail Draft Creation
===============================
Thin wrapper for modules/gmail - used by .gitlab/gmail-drafts.yml

Usage:
    DRAFTS_JSON_B64=... python scripts/ci/gmail_create_drafts.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.gmail import create_drafts_from_b64


def main():
    drafts_b64 = os.environ.get("DRAFTS_JSON_B64", "")
    
    if not drafts_b64:
        print("No DRAFTS_JSON_B64 provided")
        return 0
    
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    
    try:
        count = create_drafts_from_b64(drafts_b64, dry_run=dry_run)
        print(f"\n{'=' * 50}")
        print(f"✅ Created {count} draft(s)")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
