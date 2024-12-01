import asyncio
import os
from datetime import datetime, timedelta

from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from loguru import logger
from playwright.async_api import Browser, Page

from src.config import settings
from src.schedule.exceptions import FetchError, LoginError, ParseError


class ScheduleCrawler:
    def __init__(self, username: str, password: str, nickname: str):
        self.username = username
        self.password = password
        self.cookies = None
        self.nickname = nickname
        logger.info("Initialized ScheduleCrawler")

    async def _perform_login(self, page: Page) -> None:
        """Handle the login process on the page"""
        try:
            # Make sure the page is fully loaded
            logger.debug("Waiting for main login form...")
            main_div = await page.wait_for_selector(
                "div.main", state="visible", timeout=5000  # Reduced timeout
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
            await username_input.fill(self.username)
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
            await page.wait_for_selector(
                "div.student-selector",
                state="visible",
                timeout=15000,  # Reduced timeout
            )

            # Check if login was successful
            error_element = await page.query_selector(".error-message")
            if error_element:
                error_text = await error_element.text_content()
                raise LoginError(
                    f"Invalid credentials: {error_text}", student_nickname=self.nickname
                )

        except Exception as e:
            screenshot_path = None
            if not isinstance(e, LoginError):
                # This will capture a screenshot if the page navigation fails
                os.makedirs("data", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"data/page_failure_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
            raise LoginError(
                str(e),
                screenshot_path=screenshot_path,
                student_nickname=self.nickname,
            ) from e

    async def login(self) -> list[dict]:
        """Perform login and return cookies"""
        logger.info("Starting login process...")

        async def on_browser_created(browser: Browser):
            logger.debug("Browser created, navigating to login page...")
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            try:
                logger.debug("Navigating to login page...")
                await page.goto(str(settings.base_url))
                await self._perform_login(page)

                # Get cookies after successful login
                logger.debug("Login successful, retrieving cookies...")

                cookies = await context.cookies()
                self.cookies = cookies
                return cookies

            except Exception as e:
                raise e

        crawler_strategy = AsyncPlaywrightCrawlerStrategy(
            verbose=True, use_cached_html=False
        )
        crawler_strategy.set_hook("on_browser_created", on_browser_created)
        async with AsyncWebCrawler(
            verbose=True,
            crawler_strategy=crawler_strategy,
        ) as crawler:
            try:
                await crawler.arun(url=str(settings.schedule_url))
            except Exception as e:
                raise LoginError(
                    f"Browser error: {str(e)}", student_nickname=self.nickname
                ) from e

        logger.info("Login completed successfully")
        return self.cookies

    async def get_schedule_raw(self, date: datetime) -> list[dict]:
        """Fetch schedule HTML for a specific week"""
        try:
            formatted_date = date.strftime("%d.%m.%Y.")
            url = f"{settings.schedule_url}?Date={formatted_date}"
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
            raise FetchError(
                f"Error fetching schedule for {date}: {str(e)}",
                student_nickname=self.nickname,
            ) from e

    async def get_schedule_for_week(self, date: datetime) -> tuple[list[dict], str]:
        """Fetch schedule HTML for a specific week"""
        strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
        try:
            formatted_date = date.strftime("%d.%m.%Y.")
            url = f"{settings.schedule_url}?Date={formatted_date}"
            logger.info(f"Fetching schedule for week of {formatted_date}")

            # Use crawler with stored cookies
            logger.debug("Starting crawler for schedule extraction...")
            async with AsyncWebCrawler(
                cookies=self.cookies,
            ) as crawler:
                result = await crawler.arun(
                    url=url, use_cached_html=False, cache_mode=CacheMode.DISABLED
                )

                try:
                    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
                    raw_data = strategy.extract(html=result.html, url=url)

                    # Validate extracted data
                    if (
                        not raw_data
                        or not isinstance(raw_data, list)
                        or len(raw_data) == 0
                    ):
                        raise ParseError(
                            f"No schedule data found for {formatted_date}",
                            student_nickname=self.nickname,
                        )

                    # Check if days field exists and has data
                    first_item = raw_data[0]
                    if (
                        not isinstance(first_item, dict)
                        or "days" not in first_item
                        or not first_item["days"]
                    ):
                        raise ParseError(
                            f"Invalid schedule data format for {formatted_date}: "
                            "missing or empty days field",
                            student_nickname=self.nickname,
                        )

                    logger.info(f"Successfully extracted schedule for {formatted_date}")
                    return raw_data, result.html
                except Exception as e:
                    raise ParseError(
                        f"Failed to parse schedule HTML: {str(e)}",
                        student_nickname=self.nickname,
                    ) from e

        except Exception as e:
            if not isinstance(e, ParseError):
                raise FetchError(str(e), student_nickname=self.nickname) from e
            raise

    async def get_schedules(self) -> list[any]:
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
                "Will fetch schedules for dates: "
                f"{[d.strftime('%d.%m.%Y') for d in dates]}"
            )

            # Fetch schedules for each week in parallel with error logging
            tasks = [self.get_schedule_for_week(date) for date in dates]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for date, result in zip(dates, results, strict=False):
                if isinstance(result, Exception):
                    logger.error(
                        "Failed to get schedule for {}: {}".format(
                            date.strftime("%d.%m.%Y"), result
                        )
                    )
                    # Re-raise the exception to trigger error handling
                    raise result
                else:
                    schedules.append(result)
                    logger.info(
                        "Successfully added schedule for week of {}".format(
                            date.strftime("%d.%m.%Y")
                        )
                    )

        except Exception as e:
            if not isinstance(e, LoginError | FetchError | ParseError):
                raise FetchError(
                    f"Error getting schedules: {str(e)}", student_nickname=self.nickname
                ) from e
            raise

        logger.info(
            f"Completed fetching schedules. Retrieved {len(schedules)} weeks of data"
        )
        return schedules


async def crawl_schedules(username: str, password: str, nickname: str) -> list[str]:
    """Main function to crawl schedules"""
    logger.info("Starting schedule crawling process...")
    crawler = ScheduleCrawler(username, password, nickname)
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
                        {
                            "name": "topic",
                            "selector": "td.subject",
                            "type": "nested",
                            "fields": [
                                {"name": "text", "selector": "p", "type": "text"},
                                {
                                    "name": "links",
                                    "selector": "a:not(.file)",
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
