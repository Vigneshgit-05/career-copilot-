#!/usr/bin/env python3
import asyncio
import signal
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.core.logger import setup_logger
from src.core.workflow import CareerCopilotWorkflow
from src.core.config import settings
from src.agents.email_tracking_agent import EmailTrackingAgent
from src.agents.analytics_agent import AnalyticsAgent

logger = setup_logger(__name__)

class CareerCopilotScheduler:
    """Scheduler for automated job application workflow"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.workflow = CareerCopilotWorkflow()
        self.email_agent = EmailTrackingAgent()
        self.analytics_agent = AnalyticsAgent()
        self.is_running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
    
    def start(self):
        """Start the scheduler"""
        logger.info("Starting CareerCopilot AI Scheduler...")
        
        # Schedule job discovery and application workflow
        self.scheduler.add_job(
            func=self._run_workflow,
            trigger=IntervalTrigger(minutes=settings.SCHEDULER_INTERVAL_MINUTES),
            id='job_application_workflow',
            name='Job Discovery & Application Workflow',
            replace_existing=True
        )
        
        # Schedule email monitoring
        self.scheduler.add_job(
            func=self._monitor_emails,
            trigger=IntervalTrigger(minutes=5),
            id='email_monitoring',
            name='Email Response Monitoring',
            replace_existing=True
        )
        
        # Schedule analytics update
        self.scheduler.add_job(
            func=self._update_analytics,
            trigger=IntervalTrigger(hours=24),
            id='analytics_update',
            name='Daily Analytics Update',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"Scheduler started. Running every {settings.SCHEDULER_INTERVAL_MINUTES} minutes")
        
        # Keep the script running
        try:
            while self.is_running:
                signal.pause()
        except AttributeError:
            # Windows doesn't support signal.pause()
            import time
            while self.is_running:
                time.sleep(1)
    
    def _run_workflow(self):
        """Run the complete job application workflow"""
        logger.info("Starting automated job application workflow...")
        
        try:
            # Run async workflow
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Get user email from environment or config
            user_email = settings.GMAIL_USER_EMAIL
            
            result = loop.run_until_complete(
                self.workflow.run(user_email)
            )
            
            if result.get('status') == 'ERROR':
                logger.error(f"Workflow failed: {result.get('message')}")
            else:
                applications = result.get('applications', [])
                logger.info(f"Workflow completed. Found {len(applications)} potential applications")
                
                # Log summary
                approved = sum(1 for a in result.get('approvals', []) if a.get('status') == 'approved')
                logger.info(f"Approvals requested: {len(result.get('approvals', []))}, Approved: {approved}")
            
            loop.close()
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
    
    def _monitor_emails(self):
        """Monitor emails for responses"""
        logger.info("Checking for email responses...")
        
        try:
            result = self.email_agent.monitor_inbox()
            
            if result.get('status') == 'SUCCESS':
                new_emails = result.get('new_emails', 0)
                logger.info(f"Processed {new_emails} new email responses")
                
                # Log classifications
                classifications = result.get('classifications', {})
                for email_type, count in classifications.items():
                    if count > 0:
                        logger.info(f"  - {email_type}: {count}")
            
        except Exception as e:
            logger.error(f"Email monitoring failed: {e}")
    
    def _update_analytics(self):
        """Update analytics data"""
        logger.info("Updating analytics...")
        
        try:
            result = self.analytics_agent.update_analytics()
            
            if result.get('status') == 'SUCCESS':
                logger.info("Analytics updated successfully")
                
                # Generate and send weekly report
                report = self.analytics_agent.generate_weekly_report()
                logger.info(f"Weekly Report: {report.get('summary', {})}")
            
        except Exception as e:
            logger.error(f"Analytics update failed: {e}")
    
    def _shutdown(self, signum, frame):
        """Shutdown the scheduler gracefully"""
        logger.info("Shutting down CareerCopilot AI...")
        self.is_running = False
        self.scheduler.shutdown()
        sys.exit(0)

def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════╗
    ║     CareerCopilot AI - Your Career        ║
    ║         Personal Job Application           ║
       ║              Assistant                     ║
    ╚═══════════════════════════════════════════╝
    
    Starting CareerCopilot AI System...
    """)
    
    # Initialize components
    scheduler = CareerCopilotScheduler()
    
    # Start dashboard in separate thread
    import threading
    from src.dashboard import streamlit_app
    
    dashboard_thread = threading.Thread(
        target=lambda: streamlit_app.main(),
        daemon=True
    )
    dashboard_thread.start()
    
    # Start scheduler
    scheduler.start()

if __name__ == "__main__":
    main()