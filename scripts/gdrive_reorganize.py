#!/usr/bin/env python3
"""
Reorganize Google Drive CLARISSA folder structure per ADR-017
Creates standard folder hierarchy if missing:
  CLARISSA/
  ├── config/
  ├── notebooks/
  ├── benchmarks/
  ├── applications/
  └── invoices/
"""
import os
import sys
import json
import base64

from google.oauth2 import service_account
from googleapiclient.discovery import build

CLARISSA_FOLDER_ID = os.environ.get('GDRIVE_CLARISSA_FOLDER_ID', 'root')

REQUIRED_FOLDERS = [
    'config',
    'notebooks', 
    'benchmarks',
    'applications',
    'invoices',
    'timesheets',
    'backups'
]

def get_drive_service():
    sa_key = os.environ.get('GDRIVE_SA_KEY')
    if not sa_key:
        print("ERROR: GDRIVE_SA_KEY environment variable not set")
        sys.exit(1)
    
    try:
        creds_dict = json.loads(base64.b64decode(sa_key))
    except:
        creds_dict = json.loads(sa_key)
    
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=credentials)

def get_existing_folders(service, parent_id):
    """Get map of existing folder names to IDs."""
    query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return {f['name']: f['id'] for f in results.get('files', [])}

def create_folder(service, name, parent_id):
    """Create a new folder."""
    metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    return folder['id']

def main():
    print("Reorganizing CLARISSA folder structure...")
    service = get_drive_service()
    
    existing = get_existing_folders(service, CLARISSA_FOLDER_ID)
    folder_ids = {}
    
    for folder_name in REQUIRED_FOLDERS:
        if folder_name in existing:
            folder_ids[folder_name] = existing[folder_name]
            print(f"✓ {folder_name} exists (ID: {existing[folder_name][:8]}...)")
        else:
            folder_id = create_folder(service, folder_name, CLARISSA_FOLDER_ID)
            folder_ids[folder_name] = folder_id
            print(f"+ {folder_name} created (ID: {folder_id[:8]}...)")
    
    # Save folder IDs for reference
    output = {
        'clarissa_root': CLARISSA_FOLDER_ID,
        'folders': folder_ids
    }
    with open('gdrive_folder_ids.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n✅ Folder structure ready!")
    print(f"   Root: {CLARISSA_FOLDER_ID}")
    print(f"   Subfolders: {len(folder_ids)}")

if __name__ == '__main__':
    main()
