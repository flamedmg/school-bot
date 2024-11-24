import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from playwright.async_api import Page, Browser
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from src.schedule.preprocess import create_default_pipeline

logger = logging.getLogger(__name__)


class ScheduleCrawler:
    BASE_URL = "https://www.e-klase.lv"
    SCHEDULE_URL = "https://my.e-klase.lv/Family/Diary"

    def __init__(self, email: str, password: str, nickname: str):
        self.email = email
        self.password = password
        self.cookies = None
        self.nickname = nickname
        logger.info("Initialized ScheduleCrawler")

    async def login(self) -> List[Dict]:
        """Perform login and return cookies"""
        logger.info("Starting login process...")

        async def on_browser_created(browser: Browser):
            logger.debug("Browser created, navigating to login page...")
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            await page.goto(self.BASE_URL)

            # Make sure the page is fully loaded
            logger.debug("Waiting for main login form...")
            main_div = await page.wait_for_selector(
                "div.main", state="visible", timeout=10000
            )

            # Find elements within the main div
            username_input = await main_div.wait_for_selector(
                'input[name="UserName"]', state="visible"
            )
            password_input = await main_div.wait_for_selector(
                'input[name="Password"]', state="visible"
            )

            # Fill credentials
            logger.debug("Filling login credentials...")
            await username_input.fill(self.email)
            await password_input.fill(self.password)

            # Find and click submit button within main div
            submit_button = await main_div.wait_for_selector(
                'button[data-btn="submit"]', state="visible"
            )

            # Click and wait for navigation
            logger.debug("Submitting login form...")
            await submit_button.click()

            # Wait for navigation
            logger.debug("Waiting for successful login...")
            await page.wait_for_selector("div.student-selector", state="visible")

            # Check if login was successful
            error_element = await page.query_selector(".error-message")
            if error_element:
                logger.error("Login failed: Invalid credentials")
                raise Exception("Login failed")

            # Get cookies
            logger.debug("Login successful, retrieving cookies...")
            cookies = await context.cookies()
            self.cookies = cookies
            return cookies

        crawler_strategy = AsyncPlaywrightCrawlerStrategy(verbose=True)
        crawler_strategy.set_hook("on_browser_created", on_browser_created)
        async with AsyncWebCrawler(
            verbose=True,
            crawler_strategy=crawler_strategy,
        ) as crawler:
            result = await crawler.arun(
                url=self.SCHEDULE_URL,
            )

        logger.info("Login completed successfully")
        return self.cookies

    async def get_schedule_raw(self, date: datetime) -> List[Dict]:
        """Fetch schedule HTML for a specific week"""
        try:
            formatted_date = date.strftime("%d.%m.%Y.")
            url = f"{self.SCHEDULE_URL}?Date={formatted_date}"
            logger.info(f"Fetching raw schedule for date: {formatted_date}")

            # Use crawler with stored cookies
            async with AsyncWebCrawler(
                cookies=self.cookies,
            ) as crawler:
                result = await crawler.arun(
                    url=url,
                )
            logger.debug(f"Successfully fetched raw schedule for {formatted_date}")
            return result.html

        except Exception as e:
            logger.error(f"Error fetching schedule for {date}: {str(e)}")
            return None

    async def get_schedule_for_week(self, date: datetime) -> List[Dict]:
        """Fetch schedule HTML for a specific week"""
        strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
        pipeline = create_default_pipeline(
            nickname=self.nickname, markdown_output_path=None
        )
        try:
            formatted_date = date.strftime("%d.%m.%Y.")
            url = f"{self.SCHEDULE_URL}?Date={formatted_date}"
            logger.info(
                f"Fetching and processing schedule for week of {formatted_date}"
            )

            # Use crawler with stored cookies
            logger.debug("Starting crawler for schedule extraction...")
            async with AsyncWebCrawler(
                cookies=self.cookies,
            ) as crawler:
                result = await crawler.arun(url=url)

                strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
                raw_data = strategy.extract(html=result.html, url=url)
                 # Execute pipeline without capturing output
                logger.debug("Executing processing pipeline...")
                final_data = pipeline.execute(raw_data)
                logger.info(f"Successfully processed schedule for {formatted_date}")
                return final_data

        except Exception as e:
            logger.error(f"Error fetching schedule for {date}: {str(e)}")
            return None

    async def get_schedules(self) -> List[any]:
        """Get schedules for current week and two previous weeks"""
        schedules = []
        logger.info("Starting schedule collection for multiple weeks...")

        try:
            # Login and store cookies if not already stored
            if not self.cookies:
                logger.debug("No stored cookies found, initiating login...")
                self.cookies = await self.login()

            # Calculate dates for current and previous weeks
            current_date = datetime.now()
            dates = [
                current_date,
                current_date - timedelta(days=7),
                current_date + timedelta(days=7),
            ]
            logger.info(
                f"Will fetch schedules for dates: {[d.strftime('%d.%m.%Y') for d in dates]}"
            )

            # Fetch schedules for each week
            for date in dates:
                logger.info(f"Processing week of {date.strftime('%d.%m.%Y')}")
                schedule = await self.get_schedule_for_week(date)
                if schedule:
                    schedules.append(schedule)
                    logger.info(
                        f"Successfully added schedule for week of {date.strftime('%d.%m.%Y')}"
                    )
                else:
                    logger.error(f"Failed to get schedule for week of {date}")

        except Exception as e:
            logger.error(f"Error getting schedules: {str(e)}")

        logger.info(
            f"Completed fetching schedules. Retrieved {len(schedules)} weeks of data"
        )
        return schedules


async def crawl_schedules(email: str, password: str) -> List[str]:
    """Main function to crawl schedules"""
    logger.info("Starting schedule crawling process...")
    crawler = ScheduleCrawler(email, password)
    result = await crawler.get_schedules()
    logger.info("Schedule crawling process completed")
    return result


# Scraping Schema
JSON_SCHEMA = {
    "name": "Student Journal Lessons",
    "baseSelector": "div.student-journal-lessons-table-holder",
    "fields": [
        {
            "name": "days",
            "selector": "h2, table.lessons-table",
            "type": "nested_list",
            "fields": [
                {"name": "date", "type": "text"},
                {
                    "name": "lessons",
                    "selector": "tbody tr:not(.info)",
                    "type": "nested_list",
                    "fields": [
                        {"name": "number", "selector": "span.number", "type": "text"},
                        {"name": "subject", "selector": "span.title", "type": "text"},
                        {"name": "room", "selector": "span.room", "type": "text"},
                        {"name": "topic", "selector": "td.subject p", "type": "text"},
                        {
                            "name": "homework",
                            "type": "nested",
                            "selector": "td.hometask",
                            "fields": [
                                {"name": "text", "selector": "span p", "type": "text"},
                                {
                                    "name": "links",
                                    "selector": "a",
                                    "type": "list",
                                    "fields": [
                                        {
                                            "name": "url",
                                            "type": "attribute",
                                            "attribute": "href",
                                        }
                                    ],
                                },
                                {
                                    "name": "attachments",
                                    "selector": "a.file",
                                    "type": "list",
                                    "fields": [
                                        {"name": "filename", "type": "text"},
                                        {
                                            "name": "url",
                                            "type": "attribute",
                                            "attribute": "href",
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "name": "mark",
                            "selector": "td.score span.score",
                            "type": "list",
                            "fields": [{"name": "score", "type": "text"}],
                        },
                    ],
                },
                {
                    "name": "announcements",
                    "selector": "tr.info td.info-content p",
                    "type": "list",
                    "fields": [
                        {"name": "text", "type": "text"},
                        {
                            "name": "date",
                            "type": "attribute",
                            "attribute": "title",
                            "selector": "tr.info td.info-content p",
                        },
                    ],
                },
            ],
        }
    ],
}
