import json
import requests
from typing import Dict, Any, List, Optional
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Application, Job, Resume, Profile
from src.core.config import settings
from src.utils.validators import DataValidator

logger = setup_logger(__name__)

class ApplicationFormAgent:
    """Agent for preparing application form data"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    async def prepare_application(self, job_id: int, resume_id: int, user_id: int) -> Dict[str, Any]:
        """Prepare application data for a specific job"""
        try:
            # Get job, resume, and profile
            job = self.db.query(Job).filter(Job.id == job_id).first()
            resume = self.db.query(Resume).filter(Resume.id == resume_id).first()
            profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
            
            if not job:
                return {"status": "JOB_NOT_FOUND", "message": "Job not found"}
            
            if not resume:
                return {"status": "RESUME_NOT_FOUND", "message": "Resume not found"}
            
            if not profile:
                return {"status": "PROFILE_DATA_REQUIRED", "message": "Profile not found"}
            
            # Parse profile JSON fields
            profile_data = {
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
            
            # Validate profile completeness
            is_complete, missing_fields = DataValidator.validate_profile_completeness(profile_data)
            if not is_complete:
                return {
                    "status": "MANUAL_REVIEW_REQUIRED",
                    "message": f"Missing profile fields: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields
                }
            
            # Parse job requirements
            job_skills = json.loads(job.skills) if job.skills else []
            job_requirements = json.loads(job.requirements) if job.requirements else []
            
            # Generate application answers
            application_data = await self._generate_application_answers(
                job, profile_data, resume, job_skills, job_requirements
            )
            
            # Store application record
            application = Application(
                user_id=user_id,
                job_id=job_id,
                resume_id=resume_id,
                status='pending_approval',
                approval_status='pending'
            )
            self.db.add(application)
            self.db.commit()
            
            return {
                "status": "SUCCESS",
                "application_id": application.id,
                "application_data": application_data,
                "resume_filename": resume.filename,
                "job_details": {
                    "company": job.company,
                    "role": job.title,
                    "location": job.location,
                    "url": job.url
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to prepare application: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    async def _generate_application_answers(self, job: Job, profile: Dict, resume: Resume, 
                                            job_skills: List, job_requirements: List) -> Dict[str, Any]:
        """Generate answers for common application questions"""
        
        # Parse resume skills
        resume_skills = json.loads(resume.skills) if resume.skills else []
        
        # Standard application data
        application_data = {
            "personal_info": {
                "full_name": profile.get('name', ''),
                "first_name": profile.get('name', '').split()[0] if profile.get('name') else '',
                "last_name": ' '.join(profile.get('name', '').split()[1:]) if profile.get('name') else '',
                "email": profile.get('email', ''),
                "phone": profile.get('phone', ''),
                "location": profile.get('preferred_location', ''),
                "linkedin": profile.get('linkedin_url', ''),
                "github": profile.get('github_url', ''),
                "portfolio": profile.get('github_url', '')  # Fallback to GitHub
            },
            "professional_info": {
                "years_experience": self._extract_years_experience(profile.get('experience', [])),
                "current_salary": profile.get('expected_salary', ''),
                "expected_salary": profile.get('expected_salary', ''),
                "notice_period": profile.get('notice_period', 'Immediate'),
                "skills": profile.get('skills', []),
                "resume_skills": resume_skills,
                "job_skills_match": list(set(profile.get('skills', [])) & set(job_skills))
            },
            "answers": {
                "why_this_role": await self._generate_why_this_role(job, profile),
                "relevant_experience": await self._generate_relevant_experience(job, profile),
                "availability": f"{profile.get('notice_period', 'Immediate')} notice period",
                "salary_expectation": profile.get('expected_salary', 'Negotiable'),
                "work_authorization": "Authorized to work in the country",
                "relocation": "Yes" if profile.get('preferred_location') else "No"
            },
            "resume_info": {
                "filename": resume.filename,
                "drive_file_id": resume.drive_file_id,
                "has_resume": True
            },
            "additional_info": {
                "heard_about": "LinkedIn",
                "education_level": self._get_highest_education(profile.get('education', [])),
                "languages": ["English"]  # Default
            }
        }
        
        return application_data
    
    def _extract_years_experience(self, experience: List) -> int:
        """Extract total years of experience from experience list"""
        total_years = 0
        for exp in experience:
            if isinstance(exp, dict):
                # Try to extract years from duration string
                duration = exp.get('duration', '') or exp.get('years', '')
                import re
                years_match = re.search(r'(\d+)\s*year', duration, re.IGNORECASE)
                if years_match:
                    total_years += int(years_match.group(1))
                elif exp.get('years'):
                    total_years += int(exp.get('years', 0))
        return total_years if total_years > 0 else 3  # Default if not specified
    
    def _get_highest_education(self, education: List) -> str:
        """Get highest education level"""
        if not education:
            return "Bachelor's Degree"
        
        levels = {
            'phd': 5,
            'doctorate': 5,
            'master': 4,
            'mba': 4,
            'bachelor': 3,
            'associate': 2,
            'diploma': 1
        }
        
        highest = "Bachelor's Degree"
        highest_score = 0
        
        for edu in education:
            if isinstance(edu, dict):
                degree = edu.get('degree', '').lower()
                for level, score in levels.items():
                    if level in degree and score > highest_score:
                        highest_score = score
                        highest = edu.get('degree', "Bachelor's Degree")
        
        return highest
    
    async def _generate_why_this_role(self, job: Job, profile: Dict) -> str:
        """Generate 'Why this role' answer using Ollama"""
        try:
            skills = profile.get('skills', [])[:5]
            skills_str = ', '.join(skills) if skills else 'relevant experience'
            
            prompt = f"""Write a professional 2-3 sentence response for "Why are you interested in this role?" 

Job Title: {job.title}
Company: {job.company}
Job Description Summary: {job.description[:300] if job.description else 'N/A'}
My Top Skills: {skills_str}

Requirements:
- Keep it concise (2-3 sentences)
- Be enthusiastic but professional
- Focus on skill alignment and company interest
- Do NOT invent any experience or skills not listed"""
            
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                if generated_text and len(generated_text) < 500:
                    return generated_text
        
        except Exception as e:
            logger.error(f"Failed to generate 'why this role': {e}")
        
        # Fallback response
        skills = profile.get('skills', [])[:3]
        skills_text = ', '.join(skills) if skills else 'my skills and experience'
        return f"I am excited about the {job.title} role at {job.company} because my experience in {skills_text} aligns well with your requirements. I am confident I can contribute effectively to your team and help achieve your goals."
    
    async def _generate_relevant_experience(self, job: Job, profile: Dict) -> str:
        """Generate relevant experience summary"""
        try:
            experience_list = profile.get('experience', [])
            if not experience_list:
                return "I have relevant experience in this field and am eager to apply my skills."
            
            # Get most recent experience
            recent_exp = experience_list[0] if experience_list else {}
            company_name = recent_exp.get('company', 'my previous company')
            role = recent_exp.get('role', 'a relevant position')
            skills = profile.get('skills', [])[:5]
            skills_text = ', '.join(skills) if skills else 'key skills'
            
            prompt = f"""Write a 2-3 sentence summary of relevant experience for:
Job: {job.title} at {job.company}
My most recent role: {role} at {company_name}
My key skills: {skills_text}

Be specific about skills that match the job. Do not invent experience."""
            
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                if generated_text and len(generated_text) < 500:
                    return generated_text
        
        except Exception as e:
            logger.error(f"Failed to generate experience summary: {e}")
        
        # Fallback response
        skills = profile.get('skills', [])[:3]
        skills_text = ', '.join(skills) if skills else 'relevant skills'
        return f"In my current role, I have developed strong skills in {skills_text} which directly apply to this {job.title} position. I have successfully delivered similar projects and am confident in my ability to add value to your team."
    
    def get_application_by_id(self, application_id: int) -> Optional[Dict]:
        """Get application by ID"""
        application = self.db.query(Application).filter(Application.id == application_id).first()
        if not application:
            return None
        
        return {
            "id": application.id,
            "status": application.status,
            "approval_status": application.approval_status,
            "match_score": application.match_score,
            "ats_score": application.ats_score,
            "created_at": application.created_at.isoformat() if application.created_at else None
        }