#!/usr/bin/env python3
"""
Google Drive API Proxy - runs on GCP VM at port 8080
Allows Claude to access Google Drive via HTTP calls
"""
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os, io, json, base64

app = Flask(__name__)
SA_KEY_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '/etc/gdrive-proxy/sa-key.json')

def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        SA_KEY_PATH, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=credentials)

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "gdrive-proxy"})

@app.route('/drive/list')
def list_files():
    folder_id = request.args.get('folder_id', 'root')
    try:
        service = get_drive_service()
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            pageSize=50, fields="files(id, name, mimeType, modifiedTime, size)").execute()
        return jsonify({"success": True, "files": results.get('files', [])})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/drive/get/<file_id>')
def get_file(file_id):
    try:
        service = get_drive_service()
        file = service.files().get(fileId=file_id, fields="id,name,mimeType,modifiedTime,size,webViewLink").execute()
        return jsonify({"success": True, "file": file})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/drive/upload', methods=['POST'])
def upload_file():
    data = request.json
    try:
        service = get_drive_service()
        content = base64.b64decode(data['content_base64'])
        folder_id = data.get('folder_id', 'root')
        filename = data['filename']
        mime_type = data.get('mime_type', 'application/octet-stream')
        
        # Check if exists
        q = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        existing = service.files().list(q=q, fields="files(id)").execute().get('files', [])
        
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type)
        
        if existing:
            file = service.files().update(fileId=existing[0]['id'], media_body=media).execute()
            action = "updated"
        else:
            meta = {'name': filename, 'parents': [folder_id]}
            file = service.files().create(body=meta, media_body=media, fields='id,webViewLink').execute()
            action = "created"
        
        return jsonify({"success": True, "action": action, "file_id": file.get('id'), "link": file.get('webViewLink')})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/drive/mkdir', methods=['POST'])
def mkdir():
    data = request.json
    try:
        service = get_drive_service()
        name = data['name']
        parent_id = data.get('parent_id', 'root')
        q = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        existing = service.files().list(q=q, fields="files(id)").execute().get('files', [])
        if existing:
            return jsonify({"success": True, "folder_id": existing[0]['id'], "action": "exists"})
        meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = service.files().create(body=meta, fields='id').execute()
        return jsonify({"success": True, "folder_id": folder['id'], "action": "created"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/drive/delete/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)