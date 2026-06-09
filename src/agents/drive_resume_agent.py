import io
import json
from typing import List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pdfplumber
from docx import Document
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Resume
from src.core.config import settings

logger = setup_logger(__name__)

class GoogleDriveResumeAgent:
    """Agent for automatic resume fetching from Google Drive"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.drive_service = self._get_drive_service()
        self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    
    def _get_drive_service(self):
        """Initialize Google Drive service"""
        try:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Drive service initialization failed: {e}")
            return None
    
    def fetch_all_resumes(self) -> List[Dict[str, Any]]:
        """Fetch all resumes from Google Drive folder"""
        if not self.drive_service:
            return {"status": "ERROR", "message": "Drive service not available"}
        
        try:
            # Query for files in the specified folder
            query = f"'{self.folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            resumes = []
            
            for file in files:
                resume_data = self._process_resume_file(file)
                if resume_data:
                    resumes.append(resume_data)
                    self._store_resume_metadata(resume_data)
            
            logger.info(f"Fetched {len(resumes)} resumes from Google Drive")
            return {"status": "SUCCESS", "resumes": resumes, "count": len(resumes)}
        
        except Exception as e:
            logger.error(f"Failed to fetch resumes: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _process_resume_file(self, file: Dict) -> Dict[str, Any]:
        """Process individual resume file"""
        try:
            # Download file content
            request = self.drive_service.files().get_media(fileId=file['id'])
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            
            # Extract text based on file type
            if file['mimeType'] == 'application/pdf':
                text = self._extract_pdf_text(file_content)
            else:
                text = self._extract_docx_text(file_content)
            
            # Extract structured information
            structured_data = self._extract_resume_data(text)
            
            return {
                "drive_file_id": file['id'],
                "filename": file['name'],
                "file_type": file['mimeType'],
                "extracted_text": text,
                "skills": structured_data.get('skills', []),
                "projects": structured_data.get('projects', []),
                "experience": structured_data.get('experience', []),
                "certifications": structured_data.get('certifications', [])
            }
        except Exception as e:
            logger.error(f"Failed to process {file['name']}: {e}")
            return None
    
    def _extract_pdf_text(self, file_content) -> str:
        """Extract text from PDF"""
        text = ""
        with pdfplumber.open(file_content) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    
    def _extract_docx_text(self, file_content) -> str:
        """Extract text from DOCX"""
        doc = Document(file_content)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    def _extract_resume_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from resume text"""
        # Simple extraction - in production, use NLP or LLM
        skills = []
        projects = []
        experience = []
        certifications = []
        
        # Simple keyword extraction for skills
        common_skills = ['python', 'java', 'javascript', 'react', 'angular', 'node.js', 
                        'aws', 'azure', 'docker', 'kubernetes', 'sql', 'mongodb']
        
        text_lower = text.lower()
        for skill in common_skills:
            if skill in text_lower:
                skills.append(skill)
        
        return {
            "skills": skills,
            "projects": [],
            "experience": [],
            "certifications": []
        }
    
    def _store_resume_metadata(self, resume_data: Dict[str, Any]):
        """Store or update resume metadata in database"""
        existing = self.db.query(Resume).filter(
            Resume.drive_file_id == resume_data['drive_file_id']
        ).first()
        
        if existing:
            for key, value in resume_data.items():
                if key in ['skills', 'projects', 'experience', 'certifications']:
                    setattr(existing, key, json.dumps(value))
                else:
                    setattr(existing, key, value)
        else:
            resume = Resume(
                drive_file_id=resume_data['drive_file_id'],
                filename=resume_data['filename'],
                file_type=resume_data['file_type'],
                extracted_text=resume_data['extracted_text'],
                skills=json.dumps(resume_data.get('skills', [])),
                projects=json.dumps(resume_data.get('projects', [])),
                experience=json.dumps(resume_data.get('experience', [])),
                certifications=json.dumps(resume_data.get('certifications', []))
            )
            self.db.add(resume)
        
        self.db.commit()
    
    def get_all_resumes(self) -> List[Dict]:
        """Get all stored resumes"""
        resumes = self.db.query(Resume).all()
        return [{
            "id": r.id,
            "drive_file_id": r.drive_file_id,
            "filename": r.filename,
            "skills": json.loads(r.skills) if r.skills else []
        } for r in resumes]