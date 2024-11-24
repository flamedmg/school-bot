import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from playwright.async_api import Page, Browser

logger = logging.getLogger(__name__)

class ScheduleCrawler:
    BASE_URL = "https://www.e-klase.lv"
    SCHEDULE_URL = "https://my.e-klase.lv/Family/Diary"

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.cookies = None

    async def login(self) -> List[Dict]:
        """Perform login and return cookies"""
   
        async def on_browser_created(browser: Browser):
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            await page.goto(self.BASE_URL)
 
            # Make sure the page is fully loaded
            main_div = await page.wait_for_selector(
                'div.main',
                state="visible",
                timeout=10000
            )

            # Find elements within the main div
            username_input = await main_div.wait_for_selector(
                'input[name="UserName"]',
                state="visible"
            )
            password_input = await main_div.wait_for_selector(
                'input[name="Password"]',
                state="visible"
            )

            # Fill credentials
            await username_input.fill(self.email)
            await password_input.fill(self.password)

            # Find and click submit button within main div
            submit_button = await main_div.wait_for_selector(
                'button[data-btn="submit"]',
                state="visible"
                )
                
            # Click and wait for navigation
            await submit_button.click()
    

            # Wait for navigation
            await page.wait_for_load_state('networkidle')
                
            # Check if login was successful
            error_element = await page.query_selector('.error-message')
            if error_element:
                logger.error("Login failed: Invalid credentials")
                raise Exception("Login failed")
            
            # Get cookies
            cookies = await context.cookies()
            self.cookies = cookies
            return cookies

        crawler_strategy = AsyncPlaywrightCrawlerStrategy(verbose=True)
        crawler_strategy.set_hook('on_browser_created', on_browser_created)    
        async with AsyncWebCrawler(verbose=True, crawler_strategy=crawler_strategy) as crawler:
            result = await crawler.arun(
                url=self.SCHEDULE_URL,
            )

        return self.cookies

    async def get_schedule_for_week(self, date: datetime) -> Optional[str]:
        """Fetch schedule HTML for a specific week"""
        try:
            # ?Date=18.11.2024.
            formatted_date = date.strftime('%d.%m.%Y.')
            url = f"{self.SCHEDULE_URL}?Date={formatted_date}"
            
            # Use crawler with stored cookies
            async with AsyncWebCrawler(cookies=self.cookies) as crawler:
               result = await crawler.arun(
                    url=url,
                )
               return result.html

        except Exception as e:
            logger.error(f"Error fetching schedule for {date}: {str(e)}")
            return None

    async def get_schedules(self) -> List[str]:
        """Get schedules for current week and two previous weeks"""
        schedules = []

        try:
            # Login and store cookies if not already stored
            if not self.cookies:
                self.cookies = await self.login()

            # Calculate dates for current and previous weeks
            current_date = datetime.now()
            dates = [
                current_date,
                current_date - timedelta(days=7),
                current_date - timedelta(days=14)
            ]

            # Fetch schedules for each week
            for date in dates:
                schedule_html = await self.get_schedule_for_week(date)
                if schedule_html:
                    schedules.append(schedule_html)
                else:
                    logger.error(f"Failed to get schedule for week of {date}")

        except Exception as e:
            logger.error(f"Error getting schedules: {str(e)}")

        return schedules

async def crawl_schedules(email: str, password: str) -> List[str]:
    """Main function to crawl schedules"""
    crawler = ScheduleCrawler(email, password)
    return await crawler.get_schedules()
