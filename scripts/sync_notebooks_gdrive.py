#!/usr/bin/env python3
"""
Sync Jupyter notebooks to Google Drive /CLARISSA/notebooks folder
Generates Colab links for easy access
"""
import os
import sys
import json
import base64
from pathlib import Path
from glob import glob

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
CLARISSA_FOLDER_ID = os.environ.get('GDRIVE_CLARISSA_FOLDER_ID', '1ABC...placeholder')
NOTEBOOKS_FOLDER_NAME = 'notebooks'
NOTEBOOKS_PATH = 'docs/tutorials/*.ipynb'

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
    
    metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    print(f"Created folder: {name}")
    return folder['id']

def upload_notebook(service, filepath, folder_id):
    """Upload notebook and return Colab link."""
    filename = Path(filepath).name
    
    # Check if exists
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    existing = results.get('files', [])
    
    media = MediaFileUpload(filepath, mimetype='application/x-ipynb+json')
    
    if existing:
        file_id = existing[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
        print(f"Updated: {filename}")
    else:
        metadata = {'name': filename, 'parents': [folder_id]}
        file = service.files().create(body=metadata, media_body=media, fields='id').execute()
        file_id = file['id']
        print(f"Uploaded: {filename}")
    
    colab_url = f"https://colab.research.google.com/drive/{file_id}"
    return {'filename': filename, 'file_id': file_id, 'colab_url': colab_url}

def main():
    notebooks = glob(NOTEBOOKS_PATH)
    if not notebooks:
        print(f"SKIP: No notebooks found at {NOTEBOOKS_PATH}")
        sys.exit(0)
    
    print(f"Syncing {len(notebooks)} notebooks to Google Drive...")
    service = get_drive_service()
    
    # Find/create notebooks folder
    folder_id = find_or_create_folder(service, NOTEBOOKS_FOLDER_NAME, CLARISSA_FOLDER_ID)
    
    # Upload all notebooks
    results = []
    for nb in notebooks:
        result = upload_notebook(service, nb, folder_id)
        results.append(result)
    
    # Save results for artifact
    with open('notebook_colab_urls.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n📓 Colab Links:")
    for r in results:
        print(f"  {r['filename']}: {r['colab_url']}")
    
    print("\n✅ Notebooks sync complete!")

if __name__ == '__main__':
    main()
