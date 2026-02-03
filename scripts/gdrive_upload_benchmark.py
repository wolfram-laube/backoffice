#!/usr/bin/env python3
"""
Upload benchmark report to Google Drive /CLARISSA/benchmarks folder
"""
import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CLARISSA_FOLDER_ID = os.environ.get('GDRIVE_CLARISSA_FOLDER_ID', 'root')
BENCHMARKS_FOLDER_NAME = 'benchmarks'
BENCHMARK_FILE = os.environ.get('BENCHMARK_FILE', 'benchmark_report.json')

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

def find_or_create_folder(service, name, parent_id):
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
    return folder['id']

def upload_file(service, filepath, folder_id):
    # Add timestamp to filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_name = Path(filepath).stem
    ext = Path(filepath).suffix
    filename = f"{original_name}_{timestamp}{ext}"
    
    media = MediaFileUpload(filepath, mimetype='application/json')
    metadata = {'name': filename, 'parents': [folder_id]}
    
    file = service.files().create(
        body=metadata,
        media_body=media,
        fields='id,webViewLink'
    ).execute()
    
    return {
        'filename': filename,
        'file_id': file['id'],
        'link': file.get('webViewLink')
    }

def main():
    if not Path(BENCHMARK_FILE).exists():
        print(f"SKIP: {BENCHMARK_FILE} not found")
        sys.exit(0)
    
    print(f"Uploading benchmark report: {BENCHMARK_FILE}")
    service = get_drive_service()
    
    folder_id = find_or_create_folder(service, BENCHMARKS_FOLDER_NAME, CLARISSA_FOLDER_ID)
    result = upload_file(service, BENCHMARK_FILE, folder_id)
    
    with open('gdrive_upload_summary.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Uploaded: {result['filename']}")
    print(f"   Link: {result.get('link', 'N/A')}")

if __name__ == '__main__':
    main()
