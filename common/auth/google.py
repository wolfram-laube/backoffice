"""Google OAuth authentication."""
import pickle
from pathlib import Path
from typing import Optional, List

CONFIG_DIR = Path(__file__).parent.parent.parent / 'config' / 'google'
TOKEN_FILE = CONFIG_DIR / 'token.pickle'
CREDENTIALS_FILE = CONFIG_DIR / 'credentials.json'


def get_google_credentials(scopes: List[str]):
    """Get or refresh Google OAuth credentials."""
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise ImportError('pip install google-auth-oauthlib google-api-python-client')
    
    creds = None
    
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(f'{CREDENTIALS_FILE} not found')
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), scopes)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds


def get_gmail_service():
    """Get authenticated Gmail API service."""
    from googleapiclient.discovery import build
    creds = get_google_credentials(['https://www.googleapis.com/auth/gmail.compose'])
    return build('gmail', 'v1', credentials=creds)


def get_drive_service():
    """Get authenticated Google Drive API service."""
    from googleapiclient.discovery import build
    creds = get_google_credentials(['https://www.googleapis.com/auth/drive.file'])
    return build('drive', 'v3', credentials=creds)
