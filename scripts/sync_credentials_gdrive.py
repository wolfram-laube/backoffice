#!/usr/bin/env python3
"""
Sync credentials to Google Drive /CLARISSA/config folder
Uses CI variable GDRIVE_SA_KEY for authentication
"""
import os
import sys
import json
import base64
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
CLARISSA_FOLDER_ID = os.environ.get('GDRIVE_CLARISSA_FOLDER_ID', '1ABC...placeholder')
CONFIG_FOLDER_NAME = 'config'
CREDENTIALS_FILE = 'config/clarissa_credentials.json'

def get_drive_service():
    """Initialize Drive API with service account from CI variable."""
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

def find_or_create_folder(service, name, parent_id):
    """Find folder by name or create it."""
    query = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
    
    # Create folder
    metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    print(f"Created folder: {name}")
    return folder['id']

def upload_or_update_file(service, filepath, folder_id):
    """Upload file or update if exists."""
    filename = Path(filepath).name
    
    # Check if exists
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    existing = results.get('files', [])
    
    media = MediaFileUpload(filepath, mimetype='application/json')
    
    if existing:
        file = service.files().update(
            fileId=existing[0]['id'],
            media_body=media
        ).execute()
        print(f"Updated: {filename}")
    else:
        metadata = {'name': filename, 'parents': [folder_id]}
        file = service.files().create(
            body=metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()
        print(f"Uploaded: {filename}")
    
    return file.get('id')

def main():
    if not Path(CREDENTIALS_FILE).exists():
        print(f"SKIP: {CREDENTIALS_FILE} not found")
        sys.exit(0)
    
    print("Syncing credentials to Google Drive...")
    service = get_drive_service()
    
    # Find/create config folder
    config_folder_id = find_or_create_folder(service, CONFIG_FOLDER_NAME, CLARISSA_FOLDER_ID)
    
    # Upload credentials
    upload_or_update_file(service, CREDENTIALS_FILE, config_folder_id)
    
    print("✅ Credentials sync complete!")

if __name__ == '__main__':
    main()
