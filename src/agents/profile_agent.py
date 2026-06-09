from typing import Dict, Any
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Profile, User

logger = setup_logger(__name__)

class ProfileAgent:
    """Agent responsible for managing user profile information"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def get_or_create_profile(self, user_email: str) -> Dict[str, Any]:
        """Retrieve or create user profile"""
        try:
            user = self.db.query(User).filter(User.email == user_email).first()
            if not user:
                return {"status": "PROFILE_DATA_REQUIRED", "message": "User not found"}
            
            profile = self.db.query(Profile).filter(Profile.user_id == user.id).first()
            if not profile:
                return {"status": "PROFILE_DATA_REQUIRED", "message": "Profile incomplete"}
            
            return self._validate_profile(profile)
        except Exception as e:
            logger.error(f"Profile retrieval failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _validate_profile(self, profile: Profile) -> Dict[str, Any]:
        """Validate profile has all required fields"""
        required_fields = ['name', 'email', 'phone', 'skills', 'experience', 'education']
        
        for field in required_fields:
            if not getattr(profile, field, None):
                return {
                    "status": "PROFILE_DATA_REQUIRED",
                    "message": f"Missing field: {field}",
                    "missing_field": field
                }
        
        # Parse JSON fields
        import json
        return {
            "status": "SUCCESS",
            "profile": {
                "name": profile.name,
                "email": profile.email,
                "phone": profile.phone,
                "skills": json.loads(profile.skills) if profile.skills else [],
                "experience": json.loads(profile.experience) if profile.experience else [],
                "education": json.loads(profile.education) if profile.education else [],
                "certifications": json.loads(profile.certifications) if profile.certifications else [],
                "preferred_location": profile.preferred_location,
                "expected_salary": profile.expected_salary,
                "notice_period": profile.notice_period,
                "linkedin_url": profile.linkedin_url,
                "github_url": profile.github_url
            }
        }
    
    def update_profile(self, user_email: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile"""
        try:
            user = self.db.query(User).filter(User.email == user_email).first()
            if not user:
                user = User(email=user_email)
                self.db.add(user)
                self.db.flush()
            
            profile = self.db.query(Profile).filter(Profile.user_id == user.id).first()
            if not profile:
                profile = Profile(user_id=user.id)
            
            import json
            for key, value in profile_data.items():
                if key in ['skills', 'experience', 'education', 'certifications']:
                    setattr(profile, key, json.dumps(value))
                else:
                    setattr(profile, key, value)
            
            self.db.add(profile)
            self.db.commit()
            
            return {"status": "SUCCESS", "message": "Profile updated"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Profile update failed: {e}")
            return {"status": "ERROR", "message": str(e)}