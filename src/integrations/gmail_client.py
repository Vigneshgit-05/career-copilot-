import os
import base64
import pickle
from typing import List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from src.core.logger import setup_logger
from src.core.config import settings

logger = setup_logger(__name__)

class GmailClient:
    """Gmail API client for email operations"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        token_path = 'data/gmail_token.pickle'
        
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
        
        return build('gmail', 'v1', credentials=creds)
    
    def search_emails(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search emails using Gmail API"""
        if not self.service:
            logger.error("Gmail service not authenticated")
            return []
            
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract headers
                headers = msg.get('payload', {}).get('headers', [])
                from_addr = next((h['value'] for h in headers if h['name'] == 'From'), '')
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Extract body snippet
                snippet = msg.get('snippet', '')
                
                # Get full body if needed
                body = self._get_email_body(msg)
                
                emails.append({
                    'message_id': message['id'],
                    'thread_id': msg['threadId'],
                    'from': from_addr,
                    'subject': subject,
                    'date': date,
                    'snippet': snippet,
                    'body': body
                })
            
            return emails
        
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return []
    
    def _get_email_body(self, message: Dict) -> str:
        """Extract email body from message"""
        try:
            payload = message.get('payload', {})
            
            if 'body' in payload and payload['body'].get('data'):
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                        data = part['body']['data']
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            return message.get('snippet', '')
        
        except Exception as e:
            logger.error(f"Failed to extract email body: {e}")
            return message.get('snippet', '')
    
    def get_unread_emails(self) -> List[Dict[str, Any]]:
        """Get unread emails"""
        return self.search_emails('is:unread', max_results=30)
    
    def mark_as_read(self, message_id: str):
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")