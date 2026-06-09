from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.core.logger import setup_logger
from src.agents.profile_agent import ProfileAgent
from src.agents.drive_resume_agent import GoogleDriveResumeAgent
from src.agents.job_discovery_agent import JobDiscoveryAgent
from src.agents.jd_parser_agent import JDParserAgent
from src.agents.resume_matching_agent import ResumeMatchingAgent
from src.agents.ats_optimization_agent import ATSOptimizationAgent
from src.agents.application_form_agent import ApplicationFormAgent
from src.agents.human_approval_agent import HumanApprovalAgent
from src.agents.submission_agent import SubmissionAgent
from src.agents.email_tracking_agent import EmailTrackingAgent
from src.agents.analytics_agent import AnalyticsAgent

logger = setup_logger(__name__)

class CareerCopilotWorkflow:
    """Main workflow orchestrator using LangGraph"""
    
    def __init__(self):
        self.profile_agent = ProfileAgent()
        self.drive_agent = GoogleDriveResumeAgent()
        self.job_discovery_agent = JobDiscoveryAgent()
        self.jd_parser_agent = JDParserAgent()
        self.resume_matching_agent = ResumeMatchingAgent()
        self.ats_agent = ATSOptimizationAgent()
        self.application_agent = ApplicationFormAgent()
        self.approval_agent = HumanApprovalAgent()
        self.submission_agent = SubmissionAgent()
        self.email_agent = EmailTrackingAgent()
        self.analytics_agent = AnalyticsAgent()
        
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("get_profile", self._get_profile)
        workflow.add_node("fetch_resumes", self._fetch_resumes)
        workflow.add_node("discover_jobs", self._discover_jobs)
        workflow.add_node("parse_jd", self._parse_jd)
        workflow.add_node("match_resumes", self._match_resumes)
        workflow.add_node("ats_analysis", self._ats_analysis)
        workflow.add_node("prepare_application", self._prepare_application)
        workflow.add_node("request_approval", self._request_approval)
        workflow.add_node("submit_application", self._submit_application)
        workflow.add_node("track_emails", self._track_emails)
        workflow.add_node("update_analytics", self._update_analytics)
        
        # Define edges
        workflow.set_entry_point("get_profile")
        workflow.add_edge("get_profile", "fetch_resumes")
        workflow.add_edge("fetch_resumes", "discover_jobs")
        workflow.add_edge("discover_jobs", "parse_jd")
        workflow.add_edge("parse_jd", "match_resumes")
        workflow.add_edge("match_resumes", "ats_analysis")
        workflow.add_edge("ats_analysis", "prepare_application")
        workflow.add_edge("prepare_application", "request_approval")
        workflow.add_conditional_edges(
            "request_approval",
            self._check_approval,
            {
                "approved": "submit_application",
                "rejected": END,
                "pending": END
            }
        )
        workflow.add_edge("submit_application", "track_emails")
        workflow.add_edge("track_emails", "update_analytics")
        workflow.add_edge("update_analytics", END)
        
        return workflow.compile()
    
    async def _get_profile(self, state: Dict) -> Dict:
        """Get user profile"""
        profile = self.profile_agent.get_or_create_profile(state.get('user_email'))
        return {**state, "profile": profile}
    
    async def _fetch_resumes(self, state: Dict) -> Dict:
        """Fetch resumes from Google Drive"""
        resumes = self.drive_agent.fetch_all_resumes()
        return {**state, "resumes": resumes}
    
    async def _discover_jobs(self, state: Dict) -> Dict:
        """Discover job listings"""
        skills = state.get('profile', {}).get('profile', {}).get('skills', [])
        jobs = await self.job_discovery_agent.discover_jobs(skills)
        return {**state, "jobs": jobs}
    
    async def _parse_jd(self, state: Dict) -> Dict:
        """Parse job descriptions"""
        parsed_jobs = []
        for job in state.get('jobs', {}).get('jobs', []):
            parsed = await self.jd_parser_agent.parse_job_description(job['url'])
            parsed_jobs.append(parsed)
        return {**state, "parsed_jobs": parsed_jobs}
    
    async def _match_resumes(self, state: Dict) -> Dict:
        """Match resumes with jobs"""
        matches = []
        for job in state.get('parsed_jobs', []):
            match = self.resume_matching_agent.match_resumes_to_job(job['id'])
            matches.append(match)
        return {**state, "matches": matches}
    
    async def _ats_analysis(self, state: Dict) -> Dict:
        """Perform ATS analysis"""
        analyses = []
        for match in state.get('matches', []):
            if match.get('best_resume'):
                analysis = self.ats_agent.analyze_ats_compatibility(
                    match.get('job_id'),
                    match.get('best_resume', {}).get('text', '')
                )
                analyses.append(analysis)
        return {**state, "ats_analyses": analyses}
    
    async def _prepare_application(self, state: Dict) -> Dict:
        """Prepare application data"""
        applications = []
        for match, analysis in zip(state.get('matches', []), state.get('ats_analyses', [])):
            app = {
                "job_id": match.get('job_id'),
                "resume_id": match.get('best_resume', {}).get('resume_id'),
                "match_score": match.get('match_score'),
                "ats_score": analysis.get('ats_score'),
                "missing_keywords": analysis.get('missing_keywords', [])
            }
            applications.append(app)
        return {**state, "applications": applications}
    
    async def _request_approval(self, state: Dict) -> Dict:
        """Request human approval"""
        approvals = []
        for app in state.get('applications', []):
            approval = self.approval_agent.request_approval(app)
            approvals.append(approval)
        return {**state, "approvals": approvals}
    
    async def _submit_application(self, state: Dict) -> Dict:
        """Submit approved applications"""
        submissions = []
        for approval in state.get('approvals', []):
            if approval.get('status') == 'approved':
                submission = await self.submission_agent.submit_application(
                    approval['application_id'],
                    state.get('profile', {}).get('profile', {})
                )
                submissions.append(submission)
        return {**state, "submissions": submissions}
    
    async def _track_emails(self, state: Dict) -> Dict:
        """Track email responses"""
        tracked = self.email_agent.monitor_inbox()
        return {**state, "email_tracking": tracked}
    
    async def _update_analytics(self, state: Dict) -> Dict:
        """Update analytics"""
        analytics = self.analytics_agent.update_analytics()
        return {**state, "analytics": analytics}
    
    def _check_approval(self, state: Dict) -> str:
        """Check approval status"""
        approvals = state.get('approvals', [])
        if any(a.get('status') == 'approved' for a in approvals):
            return "approved"
        elif any(a.get('status') == 'rejected' for a in approvals):
            return "rejected"
        return "pending"
    
    async def run(self, user_email: str) -> Dict[str, Any]:
        """Run the complete workflow"""
        try:
            result = await self.workflow.ainvoke({"user_email": user_email})
            logger.info("Workflow completed successfully")
            return result
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return {"status": "ERROR", "message": str(e)}