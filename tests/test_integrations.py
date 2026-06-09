import pytest
from unittest.mock import Mock, patch
from src.integrations.telegram_bot import TelegramBot
from src.integrations.gmail_client import GmailClient

class TestTelegramBot:
    """Test Telegram Bot Integration"""
    
    def test_message_sending(self):
        bot = TelegramBot()
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'ok': True}
            
            result = bot.send_message("Test message")
            assert result == True
    
    def test_approval_request(self):
        bot = TelegramBot()
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            
            result = bot.send_approval_request("Test approval", 123)
            assert result == True

class TestGmailClient:
    """Test Gmail Client"""
    
    def test_email_search(self):
        client = GmailClient()
        
        with patch.object(client, 'service') as mock_service:
            mock_service.users().messages().list().execute.return_value = {
                'messages': [
                    {'id': 'msg1', 'threadId': 'thread1'}
                ]
            }
            
            emails = client.search_emails('test')
            # Should handle gracefully even without real credentials
            assert isinstance(emails, list)

class TestResumeParser:
    """Test Resume Parser"""
    
    def test_skill_extraction(self):
        from src.utils.resume_parser import ResumeParser
        
        parser = ResumeParser()
        skills_text = "Skills: Python, JavaScript, React, AWS, Docker"
        
        skills = parser._extract_skills(skills_text)
        assert len(skills) > 0
        assert 'python' in skills
    
    def test_contact_extraction(self):
        from src.utils.resume_parser import ResumeParser
        
        parser = ResumeParser()
        text = """
        John Doe
        john.doe@example.com
        (123) 456-7890
        linkedin.com/in/johndoe
        """
        
        contact = parser._extract_contact_info(text)
        assert 'email' in contact
        assert 'phone' in contact