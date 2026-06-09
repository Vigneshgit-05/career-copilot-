import re
import json
from typing import Dict, Any, List, Optional
import pdfplumber
from docx import Document
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class ResumeParser:
    """Advanced resume parsing utility"""
    
    def __init__(self):
        self.section_patterns = {
            'contact': r'(contact|personal|information|details)',
            'summary': r'(summary|profile|objective|about)',
            'skills': r'(skills|technologies|competencies|tech stack)',
            'experience': r'(experience|employment|work history|professional)',
            'education': r'(education|academic|qualification|degree)',
            'projects': r'(projects|portfolio|personal projects)',
            'certifications': r'(certifications|certificates|credentials)',
            'achievements': r'(achievements|awards|recognition)'
        }
    
    def parse_resume(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Parse resume and extract structured information"""
        try:
            # Extract text based on file type
            if file_type == 'application/pdf':
                text = self._extract_pdf_text(file_content)
            elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                text = self._extract_docx_text(file_content)
            else:
                return {"error": "Unsupported file type"}
            
            # Extract sections
            sections = self._extract_sections(text)
            
            # Extract specific information
            parsed_data = {
                "contact_info": self._extract_contact_info(text),
                "skills": self._extract_skills(sections.get('skills', '')),
                "experience": self._extract_experience(sections.get('experience', '')),
                "education": self._extract_education(sections.get('education', '')),
                "projects": self._extract_projects(sections.get('projects', '')),
                "certifications": self._extract_certifications(sections.get('certifications', '')),
                "summary": sections.get('summary', ''),
                "raw_text": text[:5000]  # Store first 5000 chars
            }
            
            return parsed_data
        
        except Exception as e:
            logger.error(f"Resume parsing failed: {e}")
            return {"error": str(e)}
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF"""
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX"""
        import io
        doc = Document(io.BytesIO(content))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract different sections from resume"""
        sections = {}
        lines = text.split('\n')
        
        current_section = None
        current_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if line is a section header
            section_found = None
            for section, pattern in self.section_patterns.items():
                if re.match(f'^{pattern}$', line_lower, re.IGNORECASE):
                    section_found = section
                    break
            
            if section_found:
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = section_found
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Add last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _extract_contact_info(self, text: str) -> Dict[str, str]:
        """Extract contact information"""
        contact_info = {}
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['email'] = emails[0]
        
        # Extract phone
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phone'] = phones[0]
        
        # Extract LinkedIn
        linkedin_pattern = r'(linkedin\.com/in/[\w-]+)'
        linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin:
            contact_info['linkedin'] = linkedin[0]
        
        # Extract GitHub
        github_pattern = r'(github\.com/[\w-]+)'
        github = re.findall(github_pattern, text, re.IGNORECASE)
        if github:
            contact_info['github'] = github[0]
        
        return contact_info
    
    def _extract_skills(self, skills_text: str) -> List[str]:
        """Extract skills from skills section"""
        if not skills_text:
            return []
        
        # Common skill keywords
        skill_keywords = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
            'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins',
            'sql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch',
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
            'pandas', 'numpy', 'data analysis', 'data visualization',
            'git', 'github', 'gitlab', 'ci/cd', 'agile', 'scrum', 'jira'
        ]
        
        skills_text_lower = skills_text.lower()
        found_skills = []
        
        for skill in skill_keywords:
            if skill in skills_text_lower:
                found_skills.append(skill)
        
        # Also try to extract comma-separated skills
        if ',' in skills_text:
            potential_skills = [s.strip().lower() for s in skills_text.split(',')]
            for skill in potential_skills:
                if len(skill) > 2 and skill not in found_skills:
                    found_skills.append(skill)
        
        return list(set(found_skills))[:30]  # Limit to 30 skills
    
    def _extract_experience(self, exp_text: str) -> List[Dict[str, Any]]:
        """Extract work experience"""
        experiences = []
        
        # Pattern for company and date ranges
        lines = exp_text.split('\n')
        current_exp = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for date patterns
            date_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present|current)'
            dates = re.findall(date_pattern, line, re.IGNORECASE)
            
            if dates:
                if current_exp:
                    experiences.append(current_exp)
                current_exp = {
                    'company': line.split(',')[0] if ',' in line else line[:50],
                    'start_year': dates[0][0],
                    'end_year': dates[0][1],
                    'description': []
                }
            elif current_exp and len(experiences) > 0:
                current_exp['description'].append(line)
        
        if current_exp:
            experiences.append(current_exp)
        
        return experiences[:5]  # Limit to 5 experiences
    
    def _extract_education(self, edu_text: str) -> List[Dict[str, Any]]:
        """Extract education information"""
        education = []
        
        lines = edu_text.split('\n')
        current_edu = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for degree indicators
            degree_indicators = ['bachelor', 'master', 'phd', 'b.s.', 'm.s.', 'b.a.', 'm.a.']
            if any(indicator in line.lower() for indicator in degree_indicators):
                if current_edu:
                    education.append(current_edu)
                current_edu = {
                    'degree': line,
                    'institution': '',
                    'year': ''
                }
            elif current_edu and 'institution' in current_edu:
                current_edu['description'] = line
        
        if current_edu:
            education.append(current_edu)
        
        return education[:3]  # Limit to 3 education entries
    
    def _extract_projects(self, projects_text: str) -> List[Dict[str, Any]]:
        """Extract project information"""
        projects = []
        
        lines = projects_text.split('\n')
        current_project = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if len(line) < 50 and ':' not in line:
                if current_project:
                    projects.append(current_project)
                current_project = {
                    'name': line,
                    'description': []
                }
            elif current_project:
                current_project['description'].append(line)
        
        if current_project:
            projects.append(current_project)
        
        return projects[:5]  # Limit to 5 projects
    
    def _extract_certifications(self, cert_text: str) -> List[str]:
        """Extract certifications"""
        certifications = []
        
        lines = cert_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) < 100:
                certifications.append(line)
        
        return certifications[:10]  # Limit to 10 certifications