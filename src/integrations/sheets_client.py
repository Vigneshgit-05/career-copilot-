import os
import pickle
from typing import Dict, Any, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from src.core.logger import setup_logger
from src.core.config import settings
from datetime import datetime

logger = setup_logger(__name__)

class SheetsClient:
    """Google Sheets API client for analytics storage"""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self):
        self.service = self._authenticate()
        self.spreadsheet_id = None
        self._create_or_get_spreadsheet()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        creds = None
        token_path = 'data/sheets_token.pickle'
        
        os.makedirs('data', exist_ok=True)
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                    logger.warning("Sheets credentials not found, analytics will be stored locally only")
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GOOGLE_APPLICATION_CREDENTIALS, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('sheets', 'v4', credentials=creds)
    
    def _create_or_get_spreadsheet(self):
        """Create or get existing analytics spreadsheet"""
        if not self.service:
            return
        
        try:
            # Try to find existing spreadsheet
            spreadsheet_name = "CareerCopilot Analytics"
            
            # Create new spreadsheet
            spreadsheet = {
                'properties': {
                    'title': spreadsheet_name
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'Applications',
                            'gridProperties': {'frozenRowCount': 1}
                        }
                    },
                    {
                        'properties': {
                            'title': 'Emails',
                            'gridProperties': {'frozenRowCount': 1}
                        }
                    },
                    {
                        'properties': {
                            'title': 'Analytics',
                            'gridProperties': {'frozenRowCount': 1}
                        }
                    }
                ]
            }
            
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            self.spreadsheet_id = spreadsheet['spreadsheetId']
            
            # Set up headers
            self._initialize_headers()
            
            logger.info(f"Created analytics spreadsheet: {self.spreadsheet_id}")
        
        except Exception as e:
            logger.error(f"Failed to create spreadsheet: {e}")
    
    def _initialize_headers(self):
        """Initialize column headers in all sheets"""
        headers = {
            'Applications': ['Timestamp', 'Company', 'Role', 'Match Score', 'ATS Score', 'Status', 'Job URL'],
            'Emails': ['Timestamp', 'From', 'Subject', 'Classification', 'Application ID'],
            'Analytics': ['Date', 'Applications Sent', 'Interviews', 'Offers', 'Rejections', 'Response Rate (%)']
        }
        
        for sheet_name, header_row in headers.items():
            range_name = f"{sheet_name}!A1:{chr(65 + len(header_row) - 1)}1"
            body = {
                'values': [header_row],
                'majorDimension': 'ROWS'
            }
            
            try:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                # Format header row
                requests = [{
                    'repeatCell': {
                        'range': {
                            'sheetId': self._get_sheet_id(sheet_name),
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.6},
                                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True}
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                }]
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                ).execute()
            
            except Exception as e:
                logger.error(f"Failed to initialize headers for {sheet_name}: {e}")
    
    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get sheet ID by name"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return 0
        except:
            return 0
    
    def add_application_record(self, application_data: Dict[str, Any]):
        """Add application record to sheet"""
        if not self.service or not self.spreadsheet_id:
            logger.warning("Sheets not available, skipping")
            return
        
        row = [
            datetime.now().isoformat(),
            application_data.get('company', ''),
            application_data.get('role', ''),
            application_data.get('match_score', ''),
            application_data.get('ats_score', ''),
            application_data.get('status', ''),
            application_data.get('job_url', '')
        ]
        
        try:
            body = {'values': [row]}
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Applications!A:G',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"Added application record for {application_data.get('company')}")
        
        except Exception as e:
            logger.error(f"Failed to add application record: {e}")
    
    def add_email_record(self, email_data: Dict[str, Any]):
        """Add email record to sheet"""
        if not self.service or not self.spreadsheet_id:
            return
        
        row = [
            datetime.now().isoformat(),
            email_data.get('from', ''),
            email_data.get('subject', ''),
            email_data.get('classification', ''),
            email_data.get('application_id', '')
        ]
        
        try:
            body = {'values': [row]}
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Emails!A:E',
                valueInputOption='RAW',
                body=body
            ).execute()
        except Exception as e:
            logger.error(f"Failed to add email record: {e}")
    
    def update_analytics_sheet(self, analytics_data: Dict[str, Any]):
        """Update analytics sheet with aggregated data"""
        if not self.service or not self.spreadsheet_id:
            return
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        row = [
            today,
            analytics_data.get('daily', {}).get('applications_sent', 0),
            analytics_data.get('daily', {}).get('interviews', 0),
            analytics_data.get('daily', {}).get('offers', 0),
            analytics_data.get('daily', {}).get('rejections', 0),
            analytics_data.get('daily', {}).get('response_rate', 0)
        ]
        
        try:
            body = {'values': [row]}
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Analytics!A:F',
                valueInputOption='RAW',
                body=body
            ).execute()
        except Exception as e:
            logger.error(f"Failed to update analytics sheet: {e}")