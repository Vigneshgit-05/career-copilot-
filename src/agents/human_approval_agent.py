from typing import Dict, Any
from datetime import datetime
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Application
from src.integrations.telegram_bot import send_approval_request

logger = setup_logger(__name__)

class HumanApprovalAgent:
    """Agent for managing human approval workflow"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def request_approval(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request human approval for job application"""
        try:
            # Store application with pending approval
            application = Application(
                user_id=application_data.get('user_id'),
                job_id=application_data.get('job_id'),
                resume_id=application_data.get('resume_id'),
                match_score=application_data.get('match_score'),
                ats_score=application_data.get('ats_score'),
                selected_resume=application_data.get('selected_resume'),
                missing_keywords=application_data.get('missing_keywords'),
                status='pending_approval',
                approval_status='pending'
            )
            
            self.db.add(application)
            self.db.commit()
            
            # Send approval request via Telegram
            approval_message = self._format_approval_message(application_data)
            send_approval_request(approval_message, application.id)
            
            logger.info(f"Approval requested for application {application.id}")
            
            return {
                "status": "SUCCESS",
                "application_id": application.id,
                "message": "Approval request sent"
            }
        
        except Exception as e:
            logger.error(f"Approval request failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def process_decision(self, application_id: int, decision: str) -> Dict[str, Any]:
        """Process human decision on application"""
        try:
            application = self.db.query(Application).filter(
                Application.id == application_id
            ).first()
            
            if not application:
                return {"status": "ERROR", "message": "Application not found"}
            
            if decision == "APPROVE":
                application.approval_status = 'approved'
                application.status = 'approved'
                self.db.commit()
                return {"status": "SUCCESS", "decision": "approved"}
            
            elif decision == "SKIP":
                application.approval_status = 'skipped'
                application.status = 'rejected'
                self.db.commit()
                return {"status": "SUCCESS", "decision": "skipped"}
            
            elif decision == "SAVE_FOR_LATER":
                application.approval_status = 'saved_for_later'
                self.db.commit()
                return {"status": "SUCCESS", "decision": "saved_for_later"}
            
            else:
                return {"status": "ERROR", "message": "Invalid decision"}
        
        except Exception as e:
            logger.error(f"Decision processing failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _format_approval_message(self, data: Dict) -> str:
        """Format approval request message"""
        message = f"""
📋 *New Job Application Ready for Review*

🏢 *Company:* {data.get('company', 'N/A')}
💼 *Role:* {data.get('role', 'N/A')}
📍 *Location:* {data.get('location', 'N/A')}

📊 *Match Score:* {data.get('match_score', 0)}%
📈 *ATS Score:* {data.get('ats_score', 0)}%

📄 *Selected Resume:* {data.get('selected_resume', 'N/A')}

⚠️ *Missing Keywords:*
{chr(10).join(['- ' + kw for kw in data.get('missing_keywords', [])[:5]])}

🔗 *Source:* {data.get('source', 'N/A')}

Respond with:
✅ APPROVE - Submit application
⏭️ SKIP - Reject this job
💾 SAVE_FOR_LATER - Save for later review

*Application ID:* {data.get('application_id')}
        """
        return message.strip()
    
    def get_pending_approvals(self) -> list:
        """Get all pending approvals"""
        pending = self.db.query(Application).filter(
            Application.approval_status == 'pending'
        ).all()
        
        return [{
            "id": app.id,
            "company": app.job.company if app.job else "N/A",
            "role": app.job.title if app.job else "N/A",
            "match_score": app.match_score,
            "ats_score": app.ats_score
        } for app in pending]