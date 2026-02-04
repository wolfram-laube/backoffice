#!/usr/bin/env python3
"""
BLAUWEISS EDV LLC - Google Drive Billing Uploader

Routes billing documents to structured folder hierarchy per ADR-019:

  Buchhaltung/clients/{client}/{year}/{month}/         # External (to customers)
    - invoice_AR_{nr}.pdf
    - timesheet_consolidated.pdf

  Buchhaltung/contractors/{person}/{year}/{month}/{client}/  # Internal
    - timesheet.pdf
    - honorar.pdf

Filename Conventions:
  Client docs:
    {client}_{year}-{month}_invoice_AR_{nr}.pdf
    {client}_{year}-{month}_timesheet.pdf
  
  Contractor docs:
    {person}_{client}_{year}-{month}_timesheet.pdf
    {person}_{client}_{year}-{month}_honorar.pdf

Usage:
    python upload_to_drive.py billing/output/*.pdf
    python upload_to_drive.py --dry-run billing/output/*.pdf

Environment:
    GOOGLE_SERVICE_ACCOUNT_KEY: Service account JSON (file path or content)
    GOOGLE_DRIVE_FOLDER_ID: Root folder ID for uploads
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ Google API libraries not installed")
    print("   pip install google-auth google-api-python-client")
    sys.exit(1)


SCOPES = ['https://www.googleapis.com/auth/drive']

# Known contractors (extend as needed)
KNOWN_CONTRACTORS = ['wolfram', 'ian', 'mike', 'michal']

# Known clients
KNOWN_CLIENTS = ['nemensis', 'elia', '50hertz']


@dataclass
class DocumentInfo:
    """Parsed document information."""
    category: str           # 'client' or 'contractor'
    doc_type: str           # 'invoice', 'timesheet', 'honorar', 'timesheet_consolidated'
    client: str             # Client name (e.g., 'nemensis')
    year: str               # e.g., '2026'
    month: str              # e.g., '01'
    person: Optional[str]   # Contractor name (only for contractor docs)
    target_filename: str    # Target filename in GDrive
    folder_path: str        # Target folder path


def parse_filename(filename: str) -> Optional[DocumentInfo]:
    """
    Parse filename to determine folder structure.
    
    Supported formats:
    
    Client documents:
      {client}_{year}-{month}_invoice_AR_{nr}.pdf
      {client}_{year}-{month}_timesheet.pdf
      nemensis_2026-01_invoice_AR_001.pdf
      nemensis_2026-01_timesheet.pdf
    
    Contractor documents:
      {person}_{client}_{year}-{month}_timesheet.pdf
      {person}_{client}_{year}-{month}_honorar.pdf
      wolfram_nemensis_2026-01_timesheet.pdf
      ian_nemensis_2026-01_honorar.pdf
    
    Legacy formats (auto-detected):
      AR_{nr}_{year}_{client}.pdf → client invoice
      {year}-{month}_timesheet_{client}_de.pdf → client consolidated timesheet
      {year}-{month}_timesheet_{client}_{person}_de.pdf → contractor timesheet
    """
    name = Path(filename).stem.lower()
    ext = Path(filename).suffix
    
    # Pattern 1: Contractor document
    # {person}_{client}_{year}-{month}_{doctype}.pdf
    for person in KNOWN_CONTRACTORS:
        pattern = rf'^{person}_([a-z0-9_]+)_(\d{{4}})-(\d{{2}})_(timesheet|honorar)$'
        match = re.match(pattern, name)
        if match:
            client, year, month, doc_type = match.groups()
            return DocumentInfo(
                category='contractor',
                doc_type=doc_type,
                client=client,
                year=year,
                month=month,
                person=person,
                target_filename=f"{doc_type}{ext}",
                folder_path=f"Buchhaltung/contractors/{person}/{year}/{month}/{client}"
            )
    
    # Pattern 2: Client invoice
    # {client}_{year}-{month}_invoice_AR_{nr}.pdf
    match = re.match(r'^([a-z0-9_]+)_(\d{4})-(\d{2})_invoice_ar_(\d+)$', name)
    if match:
        client, year, month, nr = match.groups()
        return DocumentInfo(
            category='client',
            doc_type='invoice',
            client=client,
            year=year,
            month=month,
            person=None,
            target_filename=f"invoice_AR_{nr}{ext}",
            folder_path=f"Buchhaltung/clients/{client}/{year}/{month}"
        )
    
    # Pattern 3: Client consolidated timesheet
    # {client}_{year}-{month}_timesheet.pdf
    match = re.match(r'^([a-z0-9_]+)_(\d{4})-(\d{2})_timesheet$', name)
    if match:
        client, year, month = match.groups()
        if client not in KNOWN_CONTRACTORS:  # Not a contractor name
            return DocumentInfo(
                category='client',
                doc_type='timesheet_consolidated',
                client=client,
                year=year,
                month=month,
                person=None,
                target_filename=f"timesheet_consolidated{ext}",
                folder_path=f"Buchhaltung/clients/{client}/{year}/{month}"
            )
    
    # Legacy Pattern A: AR_{nr}_{year}_{client}.pdf
    match = re.match(r'^ar_(\d+)_(\d{4})_([a-z0-9_]+)$', name)
    if match:
        nr, year, client = match.groups()
        # Default to month 01 - ideally extract from file date
        month = "01"
        print(f"  ⚠️ Legacy format detected: {filename}")
        print(f"     Assuming month=01. Consider renaming to: {client}_{year}-{month}_invoice_AR_{nr}{ext}")
        return DocumentInfo(
            category='client',
            doc_type='invoice',
            client=client,
            year=year,
            month=month,
            person=None,
            target_filename=f"invoice_AR_{nr}{ext}",
            folder_path=f"Buchhaltung/clients/{client}/{year}/{month}"
        )
    
    # Legacy Pattern B: {year}-{month}_timesheet_{client}[_{person}][_{lang}].pdf
    match = re.match(r'^(\d{4})-(\d{2})_timesheet_([a-z0-9_]+?)(?:_([a-z]+))?(?:_([a-z]{2}))?$', name)
    if match:
        year, month, client_or_rest, maybe_person, lang = match.groups()
        
        # Check if maybe_person is a known contractor
        if maybe_person and maybe_person in KNOWN_CONTRACTORS:
            # It's a contractor timesheet
            print(f"  ⚠️ Legacy format detected: {filename}")
            print(f"     Consider renaming to: {maybe_person}_{client_or_rest}_{year}-{month}_timesheet{ext}")
            return DocumentInfo(
                category='contractor',
                doc_type='timesheet',
                client=client_or_rest,
                year=year,
                month=month,
                person=maybe_person,
                target_filename=f"timesheet{ext}",
                folder_path=f"Buchhaltung/contractors/{maybe_person}/{year}/{month}/{client_or_rest}"
            )
        else:
            # It's a consolidated client timesheet
            print(f"  ⚠️ Legacy format detected: {filename}")
            print(f"     Consider renaming to: {client_or_rest}_{year}-{month}_timesheet{ext}")
            return DocumentInfo(
                category='client',
                doc_type='timesheet_consolidated',
                client=client_or_rest,
                year=year,
                month=month,
                person=None,
                target_filename=f"timesheet_consolidated{ext}",
                folder_path=f"Buchhaltung/clients/{client_or_rest}/{year}/{month}"
            )
    
    # Unknown format
    print(f"  ❌ Unknown filename format: {filename}")
    print(f"     Expected: {{person}}_{{client}}_{{year}}-{{month}}_timesheet.pdf")
    print(f"           or: {{client}}_{{year}}-{{month}}_invoice_AR_{{nr}}.pdf")
    return None


def get_credentials():
    """Get credentials from service account key."""
    key_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    
    if not key_path:
        print("❌ GOOGLE_SERVICE_ACCOUNT_KEY not set")
        sys.exit(1)
    
    if os.path.isfile(key_path):
        return service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    else:
        try:
            key_data = json.loads(key_path)
            return service_account.Credentials.from_service_account_info(key_data, scopes=SCOPES)
        except json.JSONDecodeError:
            print("❌ Invalid service account key")
            sys.exit(1)


def get_or_create_folder(service, parent_id: str, folder_name: str) -> str:
    """Get existing folder or create new one."""
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
    
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(
        body=file_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    print(f"     📁 Created: {folder_name}/")
    return folder['id']


def ensure_folder_path(service, root_id: str, path: str) -> str:
    """Create nested folder structure and return final folder ID."""
    current_id = root_id
    
    for folder_name in path.split('/'):
        if folder_name:
            current_id = get_or_create_folder(service, current_id, folder_name)
    
    return current_id


def upload_file(service, folder_id: str, file_path: Path, target_name: str) -> dict:
    """Upload a file to Google Drive."""
    mime_types = {
        '.pdf': 'application/pdf',
        '.typ': 'text/plain',
        '.json': 'application/json',
    }
    mime_type = mime_types.get(file_path.suffix.lower(), 'application/octet-stream')
    
    # Check if file already exists
    query = f"name='{target_name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    existing = results.get('files', [])
    
    media = MediaFileUpload(str(file_path), mimetype=mime_type)
    
    if existing:
        file = service.files().update(
            fileId=existing[0]['id'],
            media_body=media,
            supportsAllDrives=True
        ).execute()
        print(f"     🔄 Updated: {target_name}")
    else:
        file_metadata = {
            'name': target_name,
            'parents': [folder_id]
        }
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        print(f"     ✅ Uploaded: {target_name}")
    
    return file


def main():
    parser = argparse.ArgumentParser(
        description="Upload billing documents to Google Drive (ADR-019)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Filename conventions:

  Client documents (→ Buchhaltung/clients/{client}/{year}/{month}/):
    {client}_{year}-{month}_invoice_AR_{nr}.pdf
    {client}_{year}-{month}_timesheet.pdf

  Contractor documents (→ Buchhaltung/contractors/{person}/{year}/{month}/{client}/):
    {person}_{client}_{year}-{month}_timesheet.pdf
    {person}_{client}_{year}-{month}_honorar.pdf

Examples:
    nemensis_2026-01_invoice_AR_001.pdf
    wolfram_nemensis_2026-01_timesheet.pdf
    ian_nemensis_2026-01_honorar.pdf
        """
    )
    parser.add_argument("files", nargs="+", help="Files to upload")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded")
    
    args = parser.parse_args()
    
    root_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    if not root_folder_id:
        print("❌ GOOGLE_DRIVE_FOLDER_ID not set")
        sys.exit(1)
    
    # Parse and validate files
    uploads: List[Tuple[Path, DocumentInfo]] = []
    skipped = 0
    
    print("📋 Parsing filenames...\n")
    
    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"  ⚠️ File not found: {f}")
            skipped += 1
            continue
        
        info = parse_filename(path.name)
        if info:
            uploads.append((path, info))
        else:
            skipped += 1
    
    if not uploads:
        print("\n❌ No valid files to upload")
        sys.exit(1)
    
    # Group by category
    client_docs = [(p, i) for p, i in uploads if i.category == 'client']
    contractor_docs = [(p, i) for p, i in uploads if i.category == 'contractor']
    
    print(f"\n📊 Summary: {len(uploads)} files to upload, {skipped} skipped")
    print(f"   📤 {len(client_docs)} client documents (external)")
    print(f"   📥 {len(contractor_docs)} contractor documents (internal)")
    
    if args.dry_run:
        if client_docs:
            print("\n📁 Buchhaltung/clients/ (→ to customers)")
            for path, info in client_docs:
                print(f"   {path.name}")
                print(f"   └─► {info.folder_path}/{info.target_filename}")
        
        if contractor_docs:
            print("\n📁 Buchhaltung/contractors/ (→ internal)")
            for path, info in contractor_docs:
                print(f"   {path.name}")
                print(f"   └─► {info.folder_path}/{info.target_filename}")
        
        print("\n⚠️ Dry run - no files uploaded")
        return
    
    # Connect and upload
    print("\n🔐 Connecting to Google Drive...")
    credentials = get_credentials()
    service = build('drive', 'v3', credentials=credentials)
    
    if client_docs:
        print("\n📤 Uploading client documents...")
        for path, info in client_docs:
            try:
                print(f"\n   {path.name}")
                folder_id = ensure_folder_path(service, root_folder_id, info.folder_path)
                upload_file(service, folder_id, path, info.target_filename)
            except Exception as e:
                print(f"     ❌ Failed: {e}")
    
    if contractor_docs:
        print("\n📥 Uploading contractor documents...")
        for path, info in contractor_docs:
            try:
                print(f"\n   {path.name}")
                folder_id = ensure_folder_path(service, root_folder_id, info.folder_path)
                upload_file(service, folder_id, path, info.target_filename)
            except Exception as e:
                print(f"     ❌ Failed: {e}")
    
    print(f"\n✅ Done!")
    print(f"🔗 https://drive.google.com/drive/folders/{root_folder_id}")


if __name__ == "__main__":
    main()
