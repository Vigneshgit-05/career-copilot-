import os
import io
import pickle
from typing import List, Dict, Any, BinaryIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from src.core.logger import setup_logger
from src.core.config import settings

logger = setup_logger(__name__)

class GoogleDriveClient:
    """Google Drive API client for file operations"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        self.service = self._authenticate()
        self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        token_path = 'data/drive_token.pickle'
        
        os.makedirs('data', exist_ok=True)
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                    logger.error(f"Credentials file not found: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GOOGLE_APPLICATION_CREDENTIALS, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    def list_resumes(self) -> List[Dict[str, Any]]:
        """List all resume files in the configured folder"""
        if not self.service or not self.folder_id:
            logger.error("Drive service not authenticated or folder not configured")
            return []
        
        try:
            query = f"'{self.folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, modifiedTime, createdTime)",
                orderBy="modifiedTime desc"
            ).execute()
            
            return results.get('files', [])
        
        except Exception as e:
            logger.error(f"Failed to list resumes: {e}")
            return []
    
    def download_file(self, file_id: str) -> bytes:
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            return file_content.getvalue()
        
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return None
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata"""
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, createdTime, parents"
            ).execute()
            return file
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            return {}
    
    def search_files(self, filename: str) -> List[Dict[str, Any]]:
        """Search for files by name"""
        try:
            query = f"name contains '{filename}'"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType)"
            ).execute()
            return results.get('files', [])
        except Exception as e:
            logger.error(f"Failed to search files: {e}")
            return []