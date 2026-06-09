import pytest
import asyncio
from unittest.mock import Mock, patch
from src.agents.profile_agent import ProfileAgent
from src.agents.drive_resume_agent import GoogleDriveResumeAgent
from src.agents.job_discovery_agent import JobDiscoveryAgent
from src.agents.resume_matching_agent import ResumeMatchingAgent

class TestProfileAgent:
    """Test Profile Agent"""
    
    def test_profile_validation_missing_fields(self):
        agent = ProfileAgent()
        # Test with incomplete profile
        result = agent.get_or_create_profile("test@example.com")
        assert result.get('status') == 'PROFILE_DATA_REQUIRED'
    
    def test_profile_update(self):
        agent = ProfileAgent()
        profile_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'skills': ['Python', 'JavaScript']
        }
        result = agent.update_profile("john@example.com", profile_data)
        assert result.get('status') == 'SUCCESS'

class TestResumeMatchingAgent:
    """Test Resume Matching Agent"""
    
    def test_similarity_calculation(self):
        agent = ResumeMatchingAgent()
        # Test with sample texts
        text1 = "Python developer with Django experience"
        text2 = "Looking for Python developer skilled in Django"
        
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        emb1 = model.encode(text1)
        emb2 = model.encode(text2)
        
        from sentence_transformers import util
        similarity = util.cos_sim(emb1, emb2)
        
        assert similarity > 0.5  # Should be similar

@pytest.mark.asyncio
class TestJobDiscoveryAgent:
    """Test Job Discovery Agent"""
    
    async def test_search_query_generation(self):
        agent = JobDiscoveryAgent()
        skills = ['Python', 'Docker']
        queries = agent._generate_search_queries(skills)
        
        assert len(queries) > 0
        assert any('Python' in q for q in queries)
        assert any('Docker' in q for q in queries)
    
    async def test_duplicate_removal(self):
        agent = JobDiscoveryAgent()
        jobs = [
            {'url': 'https://example.com/job1', 'title': 'Job 1'},
            {'url': 'https://example.com/job1', 'title': 'Job 1'},
            {'url': 'https://example.com/job2', 'title': 'Job 2'}
        ]
        
        unique = agent._remove_duplicates(jobs)
        assert len(unique) == 2

class TestDataValidator:
    """Test Data Validator"""
    
    def test_email_validation(self):
        from src.utils.validators import DataValidator
        
        assert DataValidator.validate_email('test@example.com') == True
        assert DataValidator.validate_email('invalid-email') == False
    
    def test_url_validation(self):
        from src.utils.validators import DataValidator
        
        assert DataValidator.validate_url('https://example.com') == True
        assert DataValidator.validate_url('not-a-url') == False