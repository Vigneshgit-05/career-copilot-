import asyncio
import json
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Page, Browser
from src.core.logger import setup_logger
from src.core.config import settings

logger = setup_logger(__name__)

class BrowserAutomation:
    """Advanced browser automation utilities"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """Start browser instance"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        # Add stealth scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info("Browser started")
    
    async def close(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    async def new_page(self) -> Page:
        """Create new page"""
        return await self.context.new_page()
    
    async def wait_for_and_click(self, page: Page, selector: str, timeout: int = 10000):
        """Wait for element and click"""
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            await page.click(selector)
            return True
        except Exception as e:
            logger.error(f"Failed to click {selector}: {e}")
            return False
    
    async def fill_form(self, page: Page, form_data: Dict[str, str]):
        """Fill form fields"""
        for field_name, value in form_data.items():
            if not value:
                continue
            
            selectors = [
                f'input[name="{field_name}"]',
                f'input[id="{field_name}"]',
                f'input[placeholder*="{field_name}"]',
                f'textarea[name="{field_name}"]',
                f'textarea[id="{field_name}"]'
            ]
            
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(value)
                        logger.debug(f"Filled {field_name}")
                        break
                except:
                    continue
    
    async def extract_text(self, page: Page, selector: str) -> Optional[str]:
        """Extract text from element"""
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.text_content()
        except Exception as e:
            logger.error(f"Failed to extract text from {selector}: {e}")
        return None
    
    async def extract_all_text(self, page: Page, selector: str) -> List[str]:
        """Extract text from all matching elements"""
        try:
            elements = await page.query_selector_all(selector)
            texts = []
            for element in elements:
                text = await element.text_content()
                if text:
                    texts.append(text.strip())
            return texts
        except Exception as e:
            logger.error(f"Failed to extract texts from {selector}: {e}")
            return []
    
    async def scroll_to_bottom(self, page: Page):
        """Scroll to bottom of page"""
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
    
    async def take_screenshot(self, page: Page, name: str) -> str:
        """Take screenshot"""
        screenshot_path = f"data/screenshots/{name}_{asyncio.get_event_loop().time()}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        return screenshot_path
    
    async def handle_popups(self, page: Page):
        """Handle common popups"""
        popup_selectors = [
            'button:has-text("Close")',
            'button:has-text("Cancel")',
            'button:has-text("Dismiss")',
            '[aria-label="Close"]',
            '.modal-close'
        ]
        
        for selector in popup_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    await asyncio.sleep(0.5)
            except:
                continue
    
    async def upload_file(self, page: Page, selector: str, file_path: str):
        """Upload file"""
        try:
            file_input = await page.query_selector(selector)
            if file_input:
                await file_input.set_input_files(file_path)
                logger.info(f"Uploaded file: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
        return False
    
    async def wait_for_navigation(self, page: Page, timeout: int = 30000):
        """Wait for navigation"""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except:
            return False