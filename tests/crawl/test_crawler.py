import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from crawl4ai import AsyncWebCrawler
from src.schedule.crawler import ScheduleCrawler, crawl_schedules


@pytest.fixture
def mock_cookies():
    return [
        {"name": "sessionId", "value": "test123", "domain": ".e-klase.lv"},
        {"name": "userId", "value": "user123", "domain": ".e-klase.lv"},
    ]


@pytest.fixture
def mock_schedule_data():
    return {
        "days": [
            {
                "date": "11.11.24. pirmdiena",
                "lessons": [
                    {
                        "number": "1",
                        "subject": "Math",
                        "room": "101",
                        "topic": "Test topic",
                        "homework": {"text": "Test homework", "links": [], "attachments": []},
                        "mark": []
                    }
                ],
                "announcements": []
            }
        ]
    }


@pytest.mark.asyncio
async def test_login_success(mock_cookies):
    """Test successful login and cookie retrieval"""
    with patch("crawl4ai.AsyncWebCrawler", autospec=True) as MockCrawler:
        # Setup mock page elements
        mock_main_div = AsyncMock()
        mock_username_input = AsyncMock()
        mock_password_input = AsyncMock()
        mock_submit_button = AsyncMock()
        mock_student_selector = AsyncMock()

        # Setup mock page
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=[
            mock_main_div,  # For "div.main"
            mock_student_selector,  # For "div.student-selector"
        ])
        mock_main_div.wait_for_selector = AsyncMock(side_effect=[
            mock_username_input,  # For username input
            mock_password_input,  # For password input
            mock_submit_button,  # For submit button
        ])
        mock_page.query_selector = AsyncMock(return_value=None)  # No error message

        # Setup mock context
        mock_context = AsyncMock()
        mock_context.cookies = AsyncMock(return_value=mock_cookies)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Setup mock browser
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        # Setup mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.strategy.on_browser_created = AsyncMock()
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Create crawler and test login
        crawler = ScheduleCrawler("test@example.com", "password")
        cookies = await crawler.login()

        # Verify login flow
        assert mock_page.goto.called
        assert mock_username_input.fill.called
        assert mock_password_input.fill.called
        assert mock_submit_button.click.called
        assert mock_page.wait_for_selector.called

        # Verify cookies
        assert cookies == mock_cookies


@pytest.mark.asyncio
async def test_login_failure():
    """Test login failure handling"""
    with patch("crawl4ai.AsyncWebCrawler", autospec=True) as MockCrawler:
        # Setup mock page elements
        mock_main_div = AsyncMock()
        mock_username_input = AsyncMock()
        mock_password_input = AsyncMock()
        mock_submit_button = AsyncMock()
        mock_error_element = AsyncMock()

        # Setup mock page
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=[
            mock_main_div,  # For "div.main"
            TimeoutError("Timeout waiting for selector"),  # For "div.student-selector"
        ])
        mock_main_div.wait_for_selector = AsyncMock(side_effect=[
            mock_username_input,  # For username input
            mock_password_input,  # For password input
            mock_submit_button,  # For submit button
        ])
        mock_page.query_selector = AsyncMock(return_value=mock_error_element)  # Error element exists

        # Setup mock context
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Setup mock browser
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        # Setup mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.strategy.on_browser_created = AsyncMock()
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Test login failure
        crawler = ScheduleCrawler("test@example.com", "wrong_password")
        with pytest.raises(Exception) as exc_info:
            await crawler.login()
        assert "Login failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_schedule_for_week(mock_cookies, mock_schedule_data):
    """Test fetching schedule for a specific week"""
    with patch("crawl4ai.AsyncWebCrawler", autospec=True) as MockCrawler:
        # Setup mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.arun = AsyncMock()
        mock_crawler_instance.arun.return_value.extracted_content = [mock_schedule_data]
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Create crawler and set cookies
        crawler = ScheduleCrawler("test@example.com", "password")
        crawler.cookies = mock_cookies

        # Test getting schedule
        date = datetime.now()
        schedule = await crawler.get_schedule_for_week(date)

        # Verify schedule fetching
        assert isinstance(schedule, list)
        assert len(schedule) == 1
        assert "days" in schedule[0]
        assert len(schedule[0]["days"]) > 0


@pytest.mark.asyncio
async def test_get_schedules(mock_cookies, mock_schedule_data):
    """Test fetching schedules for all three weeks"""
    with patch("crawl4ai.AsyncWebCrawler", autospec=True) as MockCrawler:
        # Setup mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.arun = AsyncMock()
        mock_crawler_instance.arun.return_value.extracted_content = [mock_schedule_data]
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Setup login mock
        mock_login = AsyncMock(return_value=mock_cookies)

        # Create crawler
        crawler = ScheduleCrawler("test@example.com", "password")
        crawler.login = mock_login

        # Test getting schedules
        schedules = await crawler.get_schedules()

        # Verify results
        assert len(schedules) == 3  # Three weeks of schedules
        assert all(isinstance(schedule, list) for schedule in schedules)
        assert mock_login.called_once()  # Login called once
        assert MockCrawler.call_count == 3  # Called for each week


@pytest.mark.asyncio
async def test_crawl_schedules_integration():
    """Test the main crawl_schedules function"""
    with patch("src.schedule.crawler.ScheduleCrawler") as MockScheduleCrawler:
        # Setup mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.get_schedules.return_value = ["week1", "week2", "week3"]
        MockScheduleCrawler.return_value = mock_crawler_instance

        # Test crawl_schedules function
        schedules = await crawl_schedules("test@example.com", "password")

        # Verify results
        assert len(schedules) == 3
        MockScheduleCrawler.assert_called_once_with("test@example.com", "password")
        mock_crawler_instance.get_schedules.assert_called_once()
