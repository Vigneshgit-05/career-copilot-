import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import func, and_
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Application, Email, Job, Analytics, User
from src.integrations.sheets_client import SheetsClient
from src.integrations.telegram_bot import send_message
from src.core.config import settings

logger = setup_logger(__name__)

class AnalyticsAgent:
    """Agent for tracking analytics and generating reports"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.sheets_client = SheetsClient()
    
    def update_analytics(self) -> Dict[str, Any]:
        """Update analytics data in database and Google Sheets"""
        try:
            # Calculate current metrics
            today = datetime.utcnow().date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            # Get user
            user = self.db.query(User).filter(User.email == settings.GMAIL_USER_EMAIL).first()
            if not user:
                return {"status": "ERROR", "message": "User not found"}
            
            # Daily analytics
            daily = self._calculate_period_analytics(user.id, today, today)
            
            # Weekly analytics
            weekly = self._calculate_period_analytics(user.id, week_start, today)
            
            # Monthly analytics
            monthly = self._calculate_period_analytics(user.id, month_start, today)
            
            # Store in database
            self._store_analytics(user.id, 'daily', today, daily)
            self._store_analytics(user.id, 'weekly', week_start, weekly)
            self._store_analytics(user.id, 'monthly', month_start, monthly)
            
            # Update Google Sheets
            self.sheets_client.update_analytics_sheet({
                'daily': daily,
                'weekly': weekly,
                'monthly': monthly
            })
            
            logger.info(f"Analytics updated for user {user.id}: {daily['applications_sent']} applications")
            
            return {
                "status": "SUCCESS",
                "daily": daily,
                "weekly": weekly,
                "monthly": monthly
            }
        
        except Exception as e:
            logger.error(f"Analytics update failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _calculate_period_analytics(self, user_id: int, start_date, end_date) -> Dict[str, Any]:
        """Calculate analytics for a specific period"""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Applications metrics
        applications = self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.submitted_at >= start_datetime,
            Application.submitted_at <= end_datetime,
            Application.status == 'submitted'
        ).all()
        
        applications_sent = len(applications)
        
        # Email responses
        email_responses = self.db.query(Email).join(Application).filter(
            Application.user_id == user_id,
            Email.created_at >= start_datetime,
            Email.created_at <= end_datetime
        ).all()
        
        interviews = sum(1 for e in email_responses if e.classification == 'interview')
        rejections = sum(1 for e in email_responses if e.classification == 'rejection')
        offers = sum(1 for e in email_responses if e.classification == 'offer')
        assessments = sum(1 for e in email_responses if e.classification == 'assessment')
        confirmations = sum(1 for e in email_responses if e.classification == 'confirmation')
        
        # Calculate rates
        response_rate = 0
        if applications_sent > 0:
            responses = interviews + rejections + offers + assessments
            response_rate = (responses / applications_sent) * 100
        
        interview_rate = 0
        if applications_sent > 0:
            interview_rate = (interviews / applications_sent) * 100
        
        offer_rate = 0
        if applications_sent > 0:
            offer_rate = (offers / applications_sent) * 100
        
        rejection_rate = 0
        if applications_sent > 0:
            rejection_rate = (rejections / applications_sent) * 100
        
        # Average match and ATS scores
        avg_match_score = self.db.query(func.avg(Application.match_score)).filter(
            Application.user_id == user_id,
            Application.submitted_at >= start_datetime,
            Application.submitted_at <= end_datetime
        ).scalar() or 0
        
        avg_ats_score = self.db.query(func.avg(Application.ats_score)).filter(
            Application.user_id == user_id,
            Application.submitted_at >= start_datetime,
            Application.submitted_at <= end_datetime
        ).scalar() or 0
        
        # Top companies
        top_companies = self.db.query(
            Job.company,
            func.count(Application.id).label('count')
        ).join(Application).filter(
            Application.user_id == user_id,
            Application.submitted_at >= start_datetime
        ).group_by(Job.company).order_by(func.count(Application.id).desc()).limit(5).all()
        
        return {
            "applications_sent": applications_sent,
            "interviews": interviews,
            "rejections": rejections,
            "offers": offers,
            "assessments": assessments,
            "confirmations": confirmations,
            "response_rate": round(response_rate, 2),
            "interview_rate": round(interview_rate, 2),
            "offer_rate": round(offer_rate, 2),
            "rejection_rate": round(rejection_rate, 2),
            "avg_match_score": round(avg_match_score, 2),
            "avg_ats_score": round(avg_ats_score, 2),
            "top_companies": [{"company": c[0], "applications": c[1]} for c in top_companies],
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }
    
    def _store_analytics(self, user_id: int, period_type: str, period_start, data: Dict):
        """Store analytics in database"""
        # Check if analytics for this period already exists
        existing = self.db.query(Analytics).filter(
            Analytics.user_id == user_id,
            Analytics.period_type == period_type,
            Analytics.period_start == datetime.combine(period_start, datetime.min.time())
        ).first()
        
        if existing:
            existing.applications_sent = data['applications_sent']
            existing.interviews = data['interviews']
            existing.rejections = data['rejections']
            existing.offers = data['offers']
            existing.response_rate = data['response_rate']
        else:
            analytics = Analytics(
                user_id=user_id,
                period_type=period_type,
                period_start=datetime.combine(period_start, datetime.min.time()),
                period_end=datetime.utcnow(),
                applications_sent=data['applications_sent'],
                interviews=data['interviews'],
                rejections=data['rejections'],
                offers=data['offers'],
                response_rate=data['response_rate']
            )
            self.db.add(analytics)
        
        self.db.commit()
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate a detailed weekly report"""
        try:
            today = datetime.utcnow().date()
            week_start = today - timedelta(days=today.weekday())
            
            # Get user
            user = self.db.query(User).filter(User.email == settings.GMAIL_USER_EMAIL).first()
            if not user:
                return {"status": "ERROR", "message": "User not found"}
            
            analytics = self._calculate_period_analytics(user.id, week_start, today)
            
            # Get pending approvals
            pending_approvals = self.db.query(Application).filter(
                Application.user_id == user.id,
                Application.approval_status == 'pending'
            ).count()
            
            # Get application timeline
            timeline = self.db.query(
                func.date(Application.submitted_at).label('date'),
                func.count(Application.id).label('count')
            ).filter(
                Application.user_id == user.id,
                Application.submitted_at >= datetime.combine(week_start, datetime.min.time())
            ).group_by(func.date(Application.submitted_at)).all()
            
            report = {
                "period": f"{week_start.isoformat()} to {today.isoformat()}",
                "summary": analytics,
                "pending_approvals": pending_approvals,
                "timeline": [{"date": str(t[0]), "applications": t[1]} for t in timeline],
                "recommendations": self._generate_recommendations(analytics),
                "next_steps": self._generate_next_steps(analytics, pending_approvals)
            }
            
            # Send report via Telegram
            self._send_weekly_report(report)
            
            return {
                "status": "SUCCESS",
                "report": report
            }
        
        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _generate_recommendations(self, analytics: Dict) -> List[str]:
        """Generate actionable recommendations based on analytics"""
        recommendations = []
        
        if analytics['response_rate'] < 20 and analytics['applications_sent'] > 10:
            recommendations.append("📝 Low response rate (below 20%). Consider optimizing your resume for ATS systems by adding more keywords from job descriptions.")
        
        if analytics['interview_rate'] < 10 and analytics['applications_sent'] > 10:
            recommendations.append("🎯 Low interview rate. Review your resume quality and tailor your applications more specifically to each role.")
        
        if analytics['avg_match_score'] < 50:
            recommendations.append("🔍 Job matching scores are low. Refine your job search criteria and focus on roles that better align with your skills.")
        
        if analytics['avg_ats_score'] < 60:
            recommendations.append("📄 ATS scores need improvement. Add missing keywords and reformat your resume for better ATS compatibility.")
        
        if analytics['rejection_rate'] > 50 and analytics['applications_sent'] > 10:
            recommendations.append("⚠️ High rejection rate. Consider upskilling in high-demand areas or adjusting your target roles.")
        
        if not recommendations:
            recommendations.append("🎉 Great performance! Keep up the good work and maintain your application momentum.")
        
        return recommendations
    
    def _generate_next_steps(self, analytics: Dict, pending_approvals: int) -> List[str]:
        """Generate next action steps"""
        steps = []
        
        if pending_approvals > 0:
            steps.append(f"📋 Review {pending_approvals} pending application{'s' if pending_approvals > 1 else ''} in the dashboard")
        
        if analytics['avg_match_score'] < 50:
            steps.append("🎯 Update your profile skills to better match target jobs")
        
        if analytics['applications_sent'] < 5:
            steps.append("🔍 Increase job applications to improve chances of interviews")
        
        if not steps:
            steps.append("✅ Continue with current strategy and monitor for interview responses")
        
        steps.append("📊 Check dashboard for detailed analytics and tracking")
        
        return steps
    
    def _send_weekly_report(self, report: Dict):
        """Send weekly report via Telegram"""
        try:
            summary = report['summary']
            message = f"""
📊 *Weekly Career Report*

📅 Period: {report['period']}

📈 *Key Metrics:*
• Applications Sent: {summary['applications_sent']}
• Interviews: {summary['interviews']}
• Offers: {summary['offers']}
• Assessments: {summary['assessments']}
• Response Rate: {summary['response_rate']}%
• Interview Rate: {summary['interview_rate']}%

⭐ *Performance:*
• Average Match Score: {summary['avg_match_score']}%
• Average ATS Score: {summary['avg_ats_score']}%
• Pending Approvals: {report['pending_approvals']}

💡 *Recommendations:*
{chr(10).join(['• ' + rec for rec in report['recommendations']])}

📌 *Next Steps:*
{chr(10).join(['• ' + step for step in report['next_steps']])}

Keep pushing forward! 🚀
            """
            
            send_message(message)
            logger.info("Weekly report sent via Telegram")
        
        except Exception as e:
            logger.error(f"Failed to send weekly report: {e}")
    
    def get_performance_trend(self, days: int = 30) -> Dict[str, Any]:
        """Get performance trend for last N days"""
        try:
            user = self.db.query(User).filter(User.email == settings.GMAIL_USER_EMAIL).first()
            if not user:
                return {"status": "ERROR", "message": "User not found"}
            
            start_date = datetime.utcnow().date() - timedelta(days=days)
            
            # Get daily analytics
            daily_stats = self.db.query(Analytics).filter(
                Analytics.user_id == user.id,
                Analytics.period_type == 'daily',
                Analytics.period_start >= start_date
            ).order_by(Analytics.period_start).all()
            
            trend = {
                "dates": [a.period_start.strftime('%Y-%m-%d') for a in daily_stats],
                "applications": [a.applications_sent for a in daily_stats],
                "interviews": [a.interviews for a in daily_stats],
                "response_rates": [a.response_rate for a in daily_stats]
            }
            
            return {
                "status": "SUCCESS",
                "trend": trend,
                "total_applications": sum(trend['applications']),
                "total_interviews": sum(trend['interviews'])
            }
        
        except Exception as e:
            logger.error(f"Performance trend failed: {e}")
            return {"status": "ERROR", "message": str(e)}