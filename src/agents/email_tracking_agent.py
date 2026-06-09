import base64
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from email.utils import parsedate_to_datetime
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Email, Application, Job, User
from src.core.config import settings
from src.integrations.gmail_client import GmailClient
from src.integrations.telegram_bot import send_message, send_alert
from src.integrations.sheets_client import SheetsClient

logger = setup_logger(__name__)

class EmailTrackingAgent:
    """Agent for tracking email responses from job applications"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.gmail_client = GmailClient()
        self.sheets_client = SheetsClient()
    
    def monitor_inbox(self) -> Dict[str, Any]:
        """Monitor Gmail inbox for application responses"""
        try:
            # Search for job application related emails
            queries = [
                'subject:"application"',
                'subject:"interview"',
                'subject:"assessment"',
                'subject:"test"',
                'subject:"offer"',
                'subject:"rejection"',
                'subject:"thank you for applying"',
                'subject:"your application"',
                'subject:"status update"',
                'from:linkedin.com',
                'from:glassdoor.com',
                'from:indeed.com',
                'from:naukri.com',
                'from:greenhouse.io',
                'from:lever.co',
                'from:workable.com'
            ]
            
            all_emails = []
            for query in queries:
                emails = self.gmail_client.search_emails(query, max_results=15)
                all_emails.extend(emails)
            
            # Remove duplicates by message_id
            unique_emails = {}
            for email in all_emails:
                if email['message_id'] not in unique_emails:
                    unique_emails[email['message_id']] = email
            
            # Process new emails
            new_emails = []
            classifications = {
                'confirmation': 0,
                'interview': 0,
                'assessment': 0,
                'rejection': 0,
                'offer': 0,
                'other': 0
            }
            
            # Get user
            user = self.db.query(User).filter(User.email == settings.GMAIL_USER_EMAIL).first()
            
            for email in unique_emails.values():
                # Check if email already processed
                existing = self.db.query(Email).filter(
                    Email.message_id == email['message_id']
                ).first()
                
                if not existing:
                    # Classify email
                    classification = self._classify_email(email)
                    classifications[classification] += 1
                    
                    # Find associated application
                    application_id = self._find_associated_application(email, user.id if user else None)
                    
                    # Store email
                    stored_email = Email(
                        application_id=application_id,
                        message_id=email['message_id'],
                        from_address=email.get('from', ''),
                        subject=email.get('subject', ''),
                        body=email.get('body', email.get('snippet', '')),
                        classification=classification
                    )
                    
                    self.db.add(stored_email)
                    self.db.commit()
                    
                    # Add to sheets
                    self.sheets_client.add_email_record({
                        'from': email.get('from', ''),
                        'subject': email.get('subject', ''),
                        'classification': classification,
                        'application_id': application_id
                    })
                    
                    new_emails.append({
                        'id': stored_email.id,
                        'subject': email.get('subject', ''),
                        'classification': classification,
                        'application_id': application_id,
                        'from': email.get('from', '')
                    })
                    
                    # Trigger notification based on classification
                    if classification in ['interview', 'offer']:
                        self._send_positive_notification(email, classification, application_id)
                    elif classification == 'rejection':
                        self._send_rejection_notification(email, application_id)
            
            self.db.commit()
            
            if new_emails:
                logger.info(f"Processed {len(new_emails)} new emails: {classifications}")
                self._send_summary_notification(len(new_emails), classifications)
            
            return {
                "status": "SUCCESS",
                "new_emails": len(new_emails),
                "classifications": classifications,
                "emails": new_emails
            }
        
        except Exception as e:
            logger.error(f"Email monitoring failed: {e}")
            return {"status": "EMAIL_CLASSIFICATION_FAILED", "message": str(e)}
    
    def _classify_email(self, email: Dict) -> str:
        """Classify email based on subject and content"""
        subject = email.get('subject', '').lower()
        body = email.get('body', email.get('snippet', '')).lower()
        from_addr = email.get('from', '').lower()
        content = f"{subject} {body}"
        
        # Classification rules with priority order
        # Offer (highest priority)
        if any(word in content for word in [
            'offer', 'congratulations', 'selected', 'welcome to the team', 
            'you got the job', 'offer letter', 'offer of employment'
        ]):
            return 'offer'
        
        # Interview
        if any(word in content for word in [
            'interview', 'meeting', 'zoom call', 'phone screen', 'technical interview',
            'coding interview', 'onsite', 'recruiter screen', 'invite you to interview'
        ]):
            return 'interview'
        
        # Assessment/Test
        if any(word in content for word in [
            'assessment', 'test', 'challenge', 'assignment', 'take-home',
            'coding challenge', 'online assessment', 'personality test'
        ]):
            return 'assessment'
        
        # Rejection
        if any(word in content for word in [
            'reject', 'unfortunately', 'not moving forward', 'decided not to proceed',
            'thank you for your interest', 'after careful consideration',
            'positions are filled', 'not selected', 'regret to inform'
        ]):
            return 'rejection'
        
        # Confirmation
        if any(word in content for word in [
            'thank you for applying', 'application received', 'we have received',
            'application submitted', 'confirmation', 'successfully applied'
        ]):
            return 'confirmation'
        
        return 'other'
    
    def _find_associated_application(self, email: Dict, user_id: Optional[int]) -> Optional[int]:
        """Find application associated with this email"""
        try:
            if not user_id:
                return None
            
            # Extract company name from email
            from_address = email.get('from', '').lower()
            subject = email.get('subject', '').lower()
            body = email.get('body', email.get('snippet', '')).lower()
            
            # Common job platforms and their patterns
            platform_patterns = {
                'linkedin': r'linkedin\.com',
                'glassdoor': r'glassdoor\.com',
                'indeed': r'indeed\.com',
                'naukri': r'naukri\.com',
                'greenhouse': r'greenhouse\.io',
                'lever': r'lever\.co',
                'workable': r'workable\.com'
            }
            
            # Search for recent applications
            recent_apps = self.db.query(Application).filter(
                Application.user_id == user_id,
                Application.status == 'submitted',
                Application.submitted_at >= datetime.utcnow() - timedelta(days=30)
            ).order_by(Application.submitted_at.desc()).limit(50).all()
            
            for app in recent_apps:
                job = self.db.query(Job).filter(Job.id == app.job_id).first()
                if job:
                    # Check if company matches
                    company_lower = job.company.lower()
                    if company_lower in from_address or company_lower in subject or company_lower in body[:500]:
                        return app.id
                    
                    # Check platform patterns
                    for platform, pattern in platform_patterns.items():
                        if re.search(pattern, from_address) and company_lower in subject:
                            return app.id
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to find associated application: {e}")
            return None
    
    def _send_positive_notification(self, email: Dict, classification: str, application_id: Optional[int]):
        """Send notification for positive responses"""
        try:
            emoji = "🎉" if classification == 'offer' else "🎯"
            title = "OFFER RECEIVED!" if classification == 'offer' else "Interview Invitation"
            
            message = f"""
{emoji} *{title}*

*From:* {email.get('from', 'Unknown')}
*Subject:* {email.get('subject', 'No subject')}

📅 *Date:* {email.get('date', 'Unknown')}

💡 *Action Required:*
1. Check your email for details
2. Respond promptly
3. Update application status in dashboard

{'🏆 Congratulations on the offer!' if classification == 'offer' else '🎯 Good luck with the interview!'}
            """
            
            send_message(message)
            send_alert('success', f"{classification.upper()} received from {email.get('from', 'Unknown')}")
            logger.info(f"Sent {classification} notification")
        
        except Exception as e:
            logger.error(f"Failed to send positive notification: {e}")
    
    def _send_rejection_notification(self, email: Dict, application_id: Optional[int]):
        """Send notification for rejection"""
        try:
            message = f"""
📧 *Application Update*

*Status:* Rejection
*From:* {email.get('from', 'Unknown')}
*Subject:* {email.get('subject', 'No subject')}

Don't get discouraged! Keep applying and improving your applications.

💪 *Next Steps:*
• Review the rejection reason if provided
• Update your resume if needed
• Apply to 2 more jobs this week
            """
            
            send_message(message)
            logger.info(f"Sent rejection notification")
        
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {e}")
    
    def _send_summary_notification(self, count: int, classifications: Dict):
        """Send daily summary notification"""
        if count == 0:
            return
        
        summary_parts = []
        for type_name, type_count in classifications.items():
            if type_count > 0:
                emoji_map = {
                    'offer': '🏆',
                    'interview': '🎯',
                    'assessment': '📝',
                    'rejection': '📧',
                    'confirmation': '✅',
                    'other': '📨'
                }
                emoji = emoji_map.get(type_name, '📧')
                summary_parts.append(f"{emoji} {type_name}: {type_count}")
        
        if summary_parts:
            message = f"""
📬 *Email Summary*

You received {count} new email{'s' if count > 1 else ''} related to your applications:

{chr(10).join(summary_parts)}

Check the dashboard for full details!
            """
            
            send_message(message)
    
    def get_unread_application_emails(self) -> List[Dict]:
        """Get unread application-related emails"""
        try:
            user = self.db.query(User).filter(User.email == settings.GMAIL_USER_EMAIL).first()
            if not user:
                return []
            
            # Get emails from last 7 days that are not marked as read
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            emails = self.db.query(Email).filter(
                Email.created_at >= week_ago
            ).order_by(Email.created_at.desc()).all()
            
            return [{
                "id": e.id,
                "subject": e.subject,
                "from": e.from_address,
                "classification": e.classification,
                "created_at": e.created_at.isoformat(),
                "application_id": e.application_id
            } for e in emails]
        
        except Exception as e:
            logger.error(f"Failed to get unread emails: {e}")
            return []
    
    def get_response_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get response statistics for the last N days"""
        try:
            user = self.db.query(User).filter(User.email == settings.GMAIL_USER_EMAIL).first()
            if not user:
                return {"status": "ERROR", "message": "User not found"}
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            emails = self.db.query(Email).join(Application).filter(
                Application.user_id == user.id,
                Email.created_at >= start_date
            ).all()
            
            stats = {
                'total_responses': len(emails),
                'by_type': {},
                'response_rate': 0,
                'positive_rate': 0
            }
            
            for email in emails:
                stats['by_type'][email.classification] = stats['by_type'].get(email.classification, 0) + 1
            
            # Calculate rates
            total_submitted = self.db.query(Application).filter(
                Application.user_id == user.id,
                Application.submitted_at >= start_date
            ).count()
            
            if total_submitted > 0:
                stats['response_rate'] = (stats['total_responses'] / total_submitted) * 100
                positive = stats['by_type'].get('interview', 0) + stats['by_type'].get('offer', 0)
                stats['positive_rate'] = (positive / total_submitted) * 100
            
            return {
                "status": "SUCCESS",
                "stats": stats,
                "period_days": days
            }
        
        except Exception as e:
            logger.error(f"Failed to get response stats: {e}")
            return {"status": "ERROR", "message": str(e)}