import os
import pytest
import logging
from datetime import datetime
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from src.schedule.crawler import ScheduleCrawler, crawl_schedules

"""Real browser tests for e-klasse crawler

This test module performs real browser interactions with e-klasse website.
To run these tests:

1. Create your test environment file:
   cp .env.test.example .env.test
   
2. Edit .env.test with your credentials:
   EKLASSE_EMAIL=your.email@example.com
   EKLASSE_PASSWORD=your_password

3. Run the tests:
   pytest -v tests/crawl/test_real_crawler.py

The tests will automatically:
- Load credentials from .env.test file (configured in conftest.py)
- Perform real browser interactions
- Verify crawler functionality with actual data
- Show detailed progress logs during execution
"""

logger = logging.getLogger(__name__)


@pytest.fixture
def credentials():
    """Get credentials from .env.test file"""
    email = os.getenv("EKLASSE_EMAIL")
    password = os.getenv("EKLASSE_PASSWORD")

    if not email or not password:
        pytest.skip(
            "EKLASSE_EMAIL and EKLASSE_PASSWORD not found in .env.test file.\n"
            "Please create .env.test from .env.test.example with your credentials."
        )

    return {"email": email, "password": password}


@pytest.mark.asyncio
async def test_real_login(credentials):
    """Test real login to e-klasse"""
    logger.info("Starting login test")
    crawler = ScheduleCrawler(credentials["email"], credentials["password"])

    try:
        cookies = await crawler.login()
        assert cookies is not None
        assert len(cookies) > 0
        assert any(
            cookie.get("domain", "").endswith("e-klase.lv") for cookie in cookies
        )

        logger.info("Successfully logged in and retrieved cookies:")
        for cookie in cookies:
            logger.debug(f"Cookie: {cookie.get('name')}: domain={cookie.get('domain')}")

    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        pytest.fail(f"Login failed: {str(e)}")


@pytest.mark.asyncio
async def test_cookie_reuse(credentials):
    """Test that cookies are properly reused across requests"""
    logger.info("Starting cookie reuse test")
    crawler = ScheduleCrawler(credentials["email"], credentials["password"])

    try:
        # First request - should perform login
        logger.info("Performing initial login...")
        cookies = await crawler.login()
        assert cookies is not None
        initial_cookie_count = len(cookies)

        # Store initial cookies for comparison
        initial_cookies = {
            cookie.get("name"): cookie.get("value") for cookie in cookies
        }

        # Second request - should reuse cookies
        logger.info("Fetching schedule with stored cookies...")
        current_date = datetime.now()
        schedule_html = await crawler.get_schedule_raw(current_date)
        assert schedule_html is not None
        assert "licejs-my.sharepoint.com" in schedule_html

        # Verify cookies were reused
        logger.info("Verifying cookie reuse...")
        current_cookies = crawler.cookies
        current_cookie_dict = {
            cookie.get("name"): cookie.get("value") for cookie in current_cookies
        }

        # Check that essential cookies are preserved
        for name, value in initial_cookies.items():
            if name in current_cookie_dict:
                assert (
                    current_cookie_dict[name] == value
                ), f"Cookie {name} value changed"

        logger.info(
            f"Successfully verified cookie reuse - {len(current_cookies)} cookies maintained"
        )

    except Exception as e:
        logger.error(f"Cookie reuse test failed: {str(e)}")
        pytest.fail(f"Cookie reuse test failed: {str(e)}")


@pytest.mark.asyncio
async def test_real_schedule_fetch(credentials):
    """Test fetching real schedules"""
    logger.info("Starting schedule fetch test")
    crawler = ScheduleCrawler(credentials["email"], credentials["password"])

    try:
        # Get current week schedule
        schedule_data = await crawler.get_schedules()
        assert schedule_data is not None
        assert len(schedule_data) == 3
        logger.info(f"Successfully fetched {len(schedule_data)} weeks of schedule data")

    except Exception as e:
        logger.error(f"Schedule fetch failed: {str(e)}")
        pytest.fail(f"Schedule fetch failed: {str(e)}")
