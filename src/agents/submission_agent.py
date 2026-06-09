import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from playwright.async_api import async_playwright
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Application

logger = setup_logger(__name__)

class SubmissionAgent:
    """Agent for submitting job applications"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.screenshots_dir = Path("data/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    async def submit_application(self, application_id: int, profile_data: Dict) -> Dict[str, Any]:
        """Submit application using Playwright automation"""
        try:
            application = self.db.query(Application).filter(
                Application.id == application_id
            ).first()
            
            if not application:
                return {"status": "ERROR", "message": "Application not found"}
            
            if application.approval_status != 'approved':
                return {"status": "ERROR", "message": "Application not approved"}
            
            # Get job details
            job = application.job
            if not job:
                return {"status": "ERROR", "message": "Job not found"}
            
            # Submit application
            submission_result = await self._auto_fill_and_submit(job.url, profile_data)
            
            if submission_result['success']:
                # Store evidence
                application.submission_status = 'submitted'
                application.submitted_at = datetime.utcnow()
                application.submission_evidence = submission_result['evidence']
                application.status = 'submitted'
                self.db.commit()
                
                logger.info(f"Application {application_id} submitted successfully")
                
                return {
                    "status": "SUCCESS",
                    "application_id": application_id,
                    "evidence": submission_result['evidence']
                }
            else:
                application.submission_status = 'failed'
                self.db.commit()
                
                return {
                    "status": "SUBMISSION_FAILED",
                    "message": submission_result.get('error', 'Unknown error')
                }
        
        except Exception as e:
            logger.error(f"Submission failed for {application_id}: {e}")
            return {"status": "SUBMISSION_FAILED", "message": str(e)}
    
    async def _auto_fill_and_submit(self, job_url: str, profile: Dict) -> Dict:
        """Auto-fill and submit application form"""
        evidence = {
            "screenshots": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Set to True for production
                page = await browser.new_page()
                
                # Navigate to job page
                await page.goto(job_url)
                await page.wait_for_load_state("networkidle")
                
                # Take screenshot
                screenshot_path = self.screenshots_dir / f"application_{datetime.utcnow().timestamp()}_before.png"
                await page.screenshot(path=str(screenshot_path))
                evidence['screenshots'].append(str(screenshot_path))
                
                # Look for apply button
                apply_selectors = [
                    'button:has-text("Apply")',
                    'a:has-text("Apply")',
                    '.apply-button',
                    '[data-test-id="apply-button"]'
                ]
                
                applied = False
                for selector in apply_selectors:
                    try:
                        apply_btn = await page.query_selector(selector)
                        if apply_btn:
                            await apply_btn.click()
                            await page.wait_for_timeout(2000)
                            applied = True
                            break
                    except:
                        continue
                
                if not applied:
                    return {"success": False, "error": "Apply button not found"}
                
                # Fill common form fields
                await self._fill_form_fields(page, profile)
                
                # Upload resume if file input exists
                resume_input = await page.query_selector('input[type="file"]')
                if resume_input:
                    await resume_input.set_input_files("data/resume.pdf")  # Path to selected resume
                
                # Submit the form
                submit_selectors = [
                    'button:has-text("Submit")',
                    'button:has-text("Submit Application")',
                    'input[type="submit"]'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_btn = await page.query_selector(selector)
                        if submit_btn:
                            await submit_btn.click()
                            break
                    except:
                        continue
                
                await page.wait_for_timeout(3000)
                
                # Take final screenshot
                screenshot_path = self.screenshots_dir / f"application_{datetime.utcnow().timestamp()}_after.png"
                await page.screenshot(path=str(screenshot_path))
                evidence['screenshots'].append(str(screenshot_path))
                
                await browser.close()
                
                return {"success": True, "evidence": evidence}
        
        except Exception as e:
            logger.error(f"Auto-fill submission failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fill_form_fields(self, page, profile: Dict):
        """Fill common form fields"""
        field_mappings = {
            'full_name': profile.get('name', ''),
            'email': profile.get('email', ''),
            'phone': profile.get('phone', ''),
            'location': profile.get('preferred_location', ''),
            'linkedin': profile.get('linkedin_url', ''),
            'github': profile.get('github_url', '')
        }
        
        for field_name, value in field_mappings.items():
            if not value:
                continue
            
            selectors = [
                f'input[name="{field_name}"]',
                f'input[id="{field_name}"]',
                f'input[placeholder*="{field_name}"]',
                f'input[aria-label*="{field_name}"]'
            ]
            
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.fill(value)
                        break
                except:
                    continue