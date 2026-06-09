import json
from typing import Dict, Any, List
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Job

logger = setup_logger(__name__)

class ATSOptimizationAgent:
    """Agent for analyzing and optimizing resume for ATS"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def analyze_ats_compatibility(self, job_id: int, resume_text: str) -> Dict[str, Any]:
        """Analyze resume compatibility with ATS"""
        try:
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return {"status": "JOB_NOT_FOUND"}
            
            # Extract keywords from job description
            jd_keywords = self._extract_keywords(job.description or "")
            resume_keywords = self._extract_keywords(resume_text)
            
            # Calculate missing keywords
            missing_keywords = list(set(jd_keywords) - set(resume_keywords))
            
            # Calculate ATS score
            if jd_keywords:
                matched = len(set(jd_keywords) & set(resume_keywords))
                ats_score = (matched / len(jd_keywords)) * 100
            else:
                ats_score = 0
            
            # Generate recommendations
            recommendations = self._generate_recommendations(missing_keywords[:10])
            
            return {
                "status": "SUCCESS",
                "ats_score": round(ats_score, 2),
                "missing_keywords": missing_keywords[:20],
                "recommendations": recommendations,
                "total_keywords_analyzed": len(jd_keywords)
            }
        
        except Exception as e:
            logger.error(f"ATS analysis failed: {e}")
            return {"status": "ATS_ANALYSIS_FAILED", "message": str(e)}
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        # Simple extraction - in production use NLP
        common_tech_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
            'sql', 'mongodb', 'postgresql', 'mysql', 'redis',
            'agile', 'scrum', 'ci/cd', 'jenkins', 'git', 'github',
            'machine learning', 'ai', 'data science', 'analytics'
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in common_tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _generate_recommendations(self, missing_keywords: List[str]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        for keyword in missing_keywords[:5]:
            recommendations.append(f"Add '{keyword}' to your skills section")
            recommendations.append(f"Include '{keyword}' in your work experience examples")
        
        return list(set(recommendations))[:5]