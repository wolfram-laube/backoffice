#!/usr/bin/env python3
"""
List Google Drive folder contents recursively (for debugging)
Outputs JSON with full folder structure
"""
import os
import sys
import json
import base64

from google.oauth2 import service_account
from googleapiclient.discovery import build

CLARISSA_FOLDER_ID = os.environ.get('GDRIVE_CLARISSA_FOLDER_ID', 'root')

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
        creds_dict, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    return build('drive', 'v3', credentials=credentials)

def list_folder(service, folder_id, depth=0, max_depth=5):
    """Recursively list folder contents."""
    if depth > max_depth:
        return []
    
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        pageSize=100,
        fields="files(id, name, mimeType, modifiedTime, size)"
    ).execute()
    
    items = []
    for f in results.get('files', []):
        item = {
            'name': f['name'],
            'id': f['id'],
            'type': 'folder' if f['mimeType'] == 'application/vnd.google-apps.folder' else 'file',
            'mimeType': f['mimeType'],
            'modifiedTime': f.get('modifiedTime'),
            'size': f.get('size')
        }
        
        if item['type'] == 'folder':
            item['children'] = list_folder(service, f['id'], depth + 1, max_depth)
        
        items.append(item)
    
    return sorted(items, key=lambda x: (x['type'] != 'folder', x['name']))

def print_tree(items, indent=0):
    """Pretty print folder tree."""
    for item in items:
        prefix = '📁' if item['type'] == 'folder' else '📄'
        print(f"{'  ' * indent}{prefix} {item['name']}")
        if 'children' in item:
            print_tree(item['children'], indent + 1)

def main():
    print(f"Listing Google Drive folder: {CLARISSA_FOLDER_ID}")
    service = get_drive_service()
    
    structure = list_folder(service, CLARISSA_FOLDER_ID)
    
    # Save JSON
    with open('gdrive_listing.json', 'w') as f:
        json.dump(structure, f, indent=2)
    
    # Print tree
    print("\n📂 CLARISSA Folder Structure:")
    print_tree(structure)
    
    print(f"\n✅ Listing saved to gdrive_listing.json ({len(structure)} top-level items)")

if __name__ == '__main__':
    main()
