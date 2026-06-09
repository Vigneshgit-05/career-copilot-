import re
from typing import Dict, Any, List, Tuple
from datetime import datetime
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number"""
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
        return len(cleaned) >= 10 and len(cleaned) <= 15 and cleaned.isdigit()
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        pattern = r'^https?:\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(:[0-9]+)?(\/.*)?$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_skills(skills: List[str]) -> Tuple[bool, List[str]]:
        """Validate skills list"""
        if not skills:
            return False, ["Skills list is empty"]
        
        errors = []
        for skill in skills:
            if not isinstance(skill, str):
                errors.append(f"Skill must be string, got {type(skill)}")
            elif len(skill) < 2:
                errors.append(f"Skill '{skill}' is too short")
            elif len(skill) > 100:
                errors.append(f"Skill '{skill[:50]}...' is too long")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_profile_completeness(profile: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if profile has all required fields"""
        required_fields = ['name', 'email', 'phone', 'skills']
        missing_fields = []
        
        for field in required_fields:
            value = profile.get(field)
            if not value or (isinstance(value, list) and len(value) == 0):
                missing_fields.append(field)
        
        # Special validation for email
        if 'email' not in missing_fields and not DataValidator.validate_email(profile.get('email', '')):
            missing_fields.append('email_invalid')
        
        # Special validation for phone
        if 'phone' not in missing_fields and not DataValidator.validate_phone(profile.get('phone', '')):
            missing_fields.append('phone_invalid')
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def validate_job_data(job_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate job data"""
        errors = []
        
        required_fields = ['title', 'company', 'url']
        for field in required_fields:
            if not job_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        if job_data.get('url') and not DataValidator.validate_url(job_data['url']):
            errors.append(f"Invalid URL: {job_data['url']}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 5000) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def validate_ats_score(score: float) -> bool:
        """Validate ATS score is between 0 and 100"""
        return 0 <= score <= 100
    
    @staticmethod
    def validate_match_score(score: float) -> bool:
        """Validate match score is between 0 and 1"""
        return 0 <= score <= 1
    
    @staticmethod
    def validate_application_status(status: str) -> bool:
        """Validate application status"""
        valid_statuses = ['pending_approval', 'approved', 'rejected', 'submitted', 'failed', 'saved_for_later']
        return status in valid_statuses

class ProfileValidator:
    """Profile-specific validation"""
    
    @staticmethod
    def validate_experience(experience: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate work experience entries"""
        if not experience:
            return True, []  # Experience can be empty
        
        errors = []
        for idx, exp in enumerate(experience):
            if not exp.get('company'):
                errors.append(f"Experience {idx + 1}: Missing company name")
            if not exp.get('role'):
                errors.append(f"Experience {idx + 1}: Missing role")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_education(education: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate education entries"""
        if not education:
            return True, []
        
        errors = []
        for idx, edu in enumerate(education):
            if not edu.get('degree'):
                errors.append(f"Education {idx + 1}: Missing degree")
            if not edu.get('institution'):
                errors.append(f"Education {idx + 1}: Missing institution")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_notice_period(notice_period: str) -> bool:
        """Validate notice period format"""
        valid_periods = ['immediate', '15 days', '30 days', '45 days', '60 days', '90 days']
        return notice_period.lower() in valid_periods