import asyncio
from typing import List, Dict, Any, Set
from playwright.async_api import async_playwright
from src.core.logger import setup_logger
from src.core.database import SessionLocal, Job

logger = setup_logger(__name__)

class JobDiscoveryAgent:
    """Agent for discovering jobs from LinkedIn and Naukri"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    async def discover_jobs(self, skills: List[str]) -> Dict[str, Any]:
        """Discover jobs based on user skills"""
        search_queries = self._generate_search_queries(skills)
        all_jobs = []
        
        for query in search_queries:
            linkedin_jobs = await self._search_linkedin(query)
            naukri_jobs = await self._search_naukri(query)
            all_jobs.extend(linkedin_jobs)
            all_jobs.extend(naukri_jobs)
        
        # Remove duplicates
        unique_jobs = self._remove_duplicates(all_jobs)
        
        # Store in database
        stored_jobs = []
        for job in unique_jobs:
            stored = self._store_job(job)
            if stored:
                stored_jobs.append(stored)
        
        logger.info(f"Discovered {len(stored_jobs)} unique jobs")
        
        return {
            "status": "SUCCESS" if stored_jobs else "JOB_NOT_FOUND",
            "jobs": stored_jobs,
            "count": len(stored_jobs)
        }
    
    def _generate_search_queries(self, skills: List[str]) -> List[str]:
        """Generate search queries from skills"""
        queries = set()
        
        # Common job title patterns
        role_patterns = ["Engineer", "Developer", "Architect", "Specialist", "Administrator"]
        
        for skill in skills:
            queries.add(f"{skill} Engineer")
            queries.add(f"{skill} Developer")
            for pattern in role_patterns:
                queries.add(f"{skill} {pattern}")
        
        return list(queries)[:10]  # Limit to 10 queries
    
    async def _search_linkedin(self, query: str) -> List[Dict]:
        """Search LinkedIn jobs using Playwright"""
        jobs = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to LinkedIn jobs
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}"
                await page.goto(search_url)
                
                # Wait for results to load
                await page.wait_for_selector('.jobs-search__results-list', timeout=10000)
                
                # Extract job listings
                job_elements = await page.query_selector_all('.job-card-container')
                
                for element in job_elements[:5]:  # Limit to 5 per query
                    title_elem = await element.query_selector('.job-card-list__title')
                    company_elem = await element.query_selector('.job-card-container__company-name')
                    location_elem = await element.query_selector('.job-card-container__metadata-item')
                    link_elem = await element.query_selector('a')
                    
                    if title_elem and company_elem and link_elem:
                        title = await title_elem.text_content()
                        company = await company_elem.text_content()
                        location = await location_elem.text_content() if location_elem else "Not specified"
                        job_url = await link_elem.get_attribute('href')
                        
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location.strip(),
                            "url": f"https://www.linkedin.com{job_url}" if job_url else "",
                            "source": "LinkedIn"
                        })
                
                await browser.close()
        except Exception as e:
            logger.error(f"LinkedIn search failed for {query}: {e}")
        
        return jobs
    
    async def _search_naukri(self, query: str) -> List[Dict]:
        """Search Naukri jobs"""
        # Similar implementation for Naukri
        # For brevity, returning mock data
        return []
    
    def _remove_duplicates(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on URL"""
        seen_urls: Set[str] = set()
        unique_jobs = []
        
        for job in jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _store_job(self, job_data: Dict) -> Dict:
        """Store job in database"""
        existing = self.db.query(Job).filter(Job.url == job_data['url']).first()
        
        if existing:
            return {
                "id": existing.id,
                "title": existing.title,
                "company": existing.company,
                "url": existing.url
            }
        
        new_job = Job(
            url=job_data['url'],
            title=job_data.get('title'),
            company=job_data.get('company'),
            location=job_data.get('location'),
            source=job_data.get('source')
        )
        
        self.db.add(new_job)
        self.db.commit()
        
        return {
            "id": new_job.id,
            "title": new_job.title,
            "company": new_job.company,
            "url": new_job.url
        }