import asyncio
from typing import Dict, Any, Optional
import requests
from src.core.logger import setup_logger
from src.core.config import settings

logger = setup_logger(__name__)

class TelegramBot:
    """Telegram Bot for notifications and approvals"""
    
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
        self.approval_callbacks = {}
    
    def send_message(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """Send a message via Telegram"""
        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Telegram message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    
    def send_approval_request(self, message: str, application_id: int) -> bool:
        """Send approval request with inline keyboard"""
        if not self.token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            
            # Create inline keyboard for approval
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '✅ Approve', 'callback_data': f'approve_{application_id}'},
                        {'text': '⏭️ Skip', 'callback_data': f'skip_{application_id}'},
                        {'text': '💾 Save Later', 'callback_data': f'save_{application_id}'}
                    ]
                ]
            }
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': keyboard
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Approval request sent for application {application_id}")
                return True
            else:
                logger.error(f"Failed to send approval request: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Approval request failed: {e}")
            return False
    
    def send_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """Send daily summary report"""
        message = f"""
📊 *Daily Summary - {stats.get('date', 'Today')}*

✅ *Applications:* {stats.get('applications', 0)}
📧 *Responses:* {stats.get('responses', 0)}
🎯 *Interviews:* {stats.get('interviews', 0)}
💼 *Offers:* {stats.get('offers', 0)}
📈 *Response Rate:* {stats.get('response_rate', 0)}%

Keep pushing forward! 💪
        """
        
        return self.send_message(message)
    
    def send_alert(self, alert_type: str, message: str) -> bool:
        """Send alert message"""
        icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        
        icon = icons.get(alert_type, '🔔')
        formatted_message = f"{icon} *{alert_type.upper()}*: {message}"
        
        return self.send_message(formatted_message)

# Singleton instance
_bot_instance = None

def get_bot() -> TelegramBot:
    """Get or create Telegram bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot()
    return _bot_instance

def send_message(message: str, parse_mode: str = 'Markdown') -> bool:
    """Convenience function to send message"""
    return get_bot().send_message(message, parse_mode)

def send_approval_request(message: str, application_id: int) -> bool:
    """Convenience function to send approval request"""
    return get_bot().send_approval_request(message, application_id)

def send_alert(alert_type: str, message: str) -> bool:
    """Convenience function to send alert"""
    return get_bot().send_alert(alert_type, message)