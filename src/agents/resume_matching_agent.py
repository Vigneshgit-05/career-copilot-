import json
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, util
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Resume, Job

logger = setup_logger(__name__)

class ResumeMatchingAgent:
    """Agent for matching resumes against job descriptions using semantic similarity"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def match_resumes_to_job(self, job_id: int) -> Dict[str, Any]:
        """Match all resumes against a specific job"""
        try:
            # Get job details
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return {"status": "JOB_NOT_FOUND", "message": "Job not found"}
            
            # Get all resumes
            resumes = self.db.query(Resume).all()
            if not resumes:
                return {"status": "RESUME_NOT_FOUND", "message": "No resumes found"}
            
            # Create embeddings
            job_embedding = self.model.encode(job.description or job.title, convert_to_tensor=True)
            
            resume_scores = []
            for resume in resumes:
                resume_text = resume.extracted_text or ""
                if resume_text:
                    resume_embedding = self.model.encode(resume_text, convert_to_tensor=True)
                    similarity = util.cos_sim(job_embedding, resume_embedding).item()
                    
                    resume_scores.append({
                        "resume_id": resume.id,
                        "filename": resume.filename,
                        "score": float(similarity),
                        "skills": json.loads(resume.skills) if resume.skills else []
                    })
            
            # Sort by score descending
            resume_scores.sort(key=lambda x: x['score'], reverse=True)
            
            if not resume_scores:
                return {"status": "NO_MATCH", "message": "No matching resumes found"}
            
            best_resume = resume_scores[0]
            
            return {
                "status": "SUCCESS",
                "best_resume": best_resume,
                "match_score": best_resume['score'],
                "resume_ranking": resume_scores[:5],
                "total_resumes_analyzed": len(resume_scores)
            }
        
        except Exception as e:
            logger.error(f"Resume matching failed: {e}")
            return {"status": "ERROR", "message": str(e)}