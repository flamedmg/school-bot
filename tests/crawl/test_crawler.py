import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def mock_cookies():
    return [
        {"name": "sessionId", "value": "test123", "domain": ".e-klase.lv"},
        {"name": "userId", "value": "user123", "domain": ".e-klase.lv"},
    ]


@pytest.fixture
def mock_schedule_data():
    return [
        {
            "days": [
                {
                    "date": "11.11.24. pirmdiena",
                    "lessons": [
                        {
                            "number": "1",
                            "subject": "Math",
                            "room": "101",
                            "topic": "Test topic",
                            "homework": {
                                "text": "Test homework",
                                "links": [],
                                "attachments": [],
                            },
                            "mark": [],
                        }
                    ],
                    "announcements": [],
                }
            ]
        }
    ]


@pytest.fixture
def mock_element():
    """Fixture for mocking page elements"""
    element = AsyncMock()
    element.wait_for_selector = AsyncMock(return_value=element)
    element.fill = AsyncMock()
    element.click = AsyncMock()
    element.text_content = AsyncMock(return_value="")
    return element


@pytest.fixture
def mock_page(mock_element):
    """Fixture for page mock with pre-configured methods"""
    page = AsyncMock()
    page.goto = AsyncMock()

    # Configure wait_for_selector to return mock_element for all selectors
    async def mock_wait_for_selector(selector, **kwargs):
        return mock_element

    page.wait_for_selector = AsyncMock(side_effect=mock_wait_for_selector)

    page.query_selector = AsyncMock(return_value=None)
    page.screenshot = AsyncMock()
    return page


@pytest.mark.asyncio
async def test_login_success(mock_cookies, mock_page, mock_element):
    """Test successful login and cookie retrieval"""
    from src.schedule.crawler import ScheduleCrawler

    with (
        patch("crawl4ai.AsyncWebCrawler") as MockCrawler,
        patch(
            "crawl4ai.async_crawler_strategy.AsyncPlaywrightCrawlerStrategy"
        ) as MockStrategy,
    ):
        # Configure strategy
        strategy = MockStrategy.return_value
        strategy.set_hook = MagicMock()

        # Configure crawler
        crawler_instance = AsyncMock()
        crawler_instance.arun = AsyncMock()
        MockCrawler.return_value.__aenter__.return_value = crawler_instance

        # Configure context
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.cookies = AsyncMock(return_value=mock_cookies)

        # Configure browser
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        # Create crawler
        crawler = ScheduleCrawler("test@example.com", "password", "test_student")

        # Execute login
        cookies = await crawler.login()

        # Verify the hook was set and execute it
        strategy.set_hook.assert_called_once()
        callback = strategy.set_hook.call_args[0][1]
        result = await callback(mock_browser)

        # Verify the login flow
        assert mock_page.goto.called
        assert mock_page.wait_for_selector.called
        assert cookies == mock_cookies
        assert result == mock_cookies


@pytest.mark.asyncio
async def test_login_failure(mock_page, mock_element):
    """Test login failure handling"""
    from src.schedule.crawler import ScheduleCrawler
    from src.schedule.exceptions import LoginError

    # Configure error element
    error_element = AsyncMock()
    error_element.text_content = AsyncMock(return_value="Invalid credentials")
    mock_page.query_selector = AsyncMock(return_value=error_element)

    with (
        patch("crawl4ai.AsyncWebCrawler") as MockCrawler,
        patch(
            "crawl4ai.async_crawler_strategy.AsyncPlaywrightCrawlerStrategy"
        ) as MockStrategy,
    ):
        # Configure strategy
        strategy = MockStrategy.return_value
        strategy.set_hook = MagicMock()

        # Configure crawler
        crawler_instance = AsyncMock()
        crawler_instance.arun = AsyncMock()
        MockCrawler.return_value.__aenter__.return_value = crawler_instance

        # Configure context and browser
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        # Create crawler
        crawler = ScheduleCrawler("test@example.com", "wrong_password", "test_student")

        # Execute login and expect failure
        with pytest.raises(LoginError) as exc_info:
            await crawler.login()
            callback = strategy.set_hook.call_args[0][1]
            await callback(mock_browser)

        assert "Invalid credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_error():
    """Test fetch error handling"""
    from src.schedule.crawler import ScheduleCrawler
    from src.schedule.exceptions import FetchError

    with patch("crawl4ai.AsyncWebCrawler") as MockCrawler:
        # Configure crawler to raise error
        crawler_instance = AsyncMock()
        crawler_instance.arun = AsyncMock(side_effect=Exception("Network error"))
        MockCrawler.return_value.__aenter__.return_value = crawler_instance

        # Configure context manager to properly propagate the exception
        MockCrawler.return_value.__aexit__ = AsyncMock(return_value=False)

        # Create crawler
        crawler = ScheduleCrawler("test@example.com", "password", "test_student")
        crawler.cookies = [{"name": "test", "value": "test"}]

        # Test get_schedule_raw with network error
        with pytest.raises(FetchError) as exc_info:
            await crawler.get_schedule_raw(datetime.now())

        assert "Network error" in str(exc_info.value)
        assert crawler.nickname in str(exc_info.value)


@pytest.mark.asyncio
async def test_parse_error(mock_cookies):
    """Test parse error handling"""
    from src.schedule.crawler import ScheduleCrawler
    from src.schedule.exceptions import ParseError

    with (
        patch("crawl4ai.AsyncWebCrawler") as MockCrawler,
        patch(
            "crawl4ai.extraction_strategy.JsonCssExtractionStrategy.extract"
        ) as mock_extract,
    ):
        # Configure crawler
        crawler_instance = AsyncMock()
        crawler_instance.arun = AsyncMock()
        MockCrawler.return_value.__aenter__.return_value = crawler_instance
        MockCrawler.return_value.__aexit__ = AsyncMock(return_value=None)

        # Configure extract to raise error
        mock_extract.side_effect = Exception("Invalid HTML structure")

        # Create crawler
        crawler = ScheduleCrawler("test@example.com", "password", "test_student")
        crawler.cookies = mock_cookies

        with pytest.raises(ParseError) as exc_info:
            await crawler.get_schedule_for_week(datetime.now())

        assert "Invalid HTML structure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_schedules(mock_cookies, mock_schedule_data):
    """Test fetching schedules for all three weeks"""
    from src.schedule.crawler import ScheduleCrawler

    with (
        patch("crawl4ai.AsyncWebCrawler") as MockCrawler,
        patch(
            "crawl4ai.extraction_strategy.JsonCssExtractionStrategy.extract"
        ) as mock_extract,
    ):
        # Configure crawler
        crawler_instance = AsyncMock()
        crawler_instance.arun = AsyncMock()
        crawler_instance.arun.return_value = AsyncMock(html="<html>test</html>")
        MockCrawler.return_value.__aenter__.return_value = crawler_instance
        MockCrawler.return_value.__aexit__ = AsyncMock(return_value=None)

        # Configure extraction
        mock_extract.return_value = mock_schedule_data

        # Create crawler with pre-set cookies
        crawler = ScheduleCrawler("test@example.com", "password", "test_student")
        crawler.cookies = mock_cookies

        # Test getting schedules
        schedules = await crawler.get_schedules()

        # Should return 3 tuples of (raw_data, html_content)
        assert len(schedules) == 3
        assert all(isinstance(schedule, tuple) for schedule in schedules)
        assert all(
            len(schedule) == 2 for schedule in schedules
        )  # Each tuple has 2 items
        assert all(
            schedule[0] == mock_schedule_data for schedule in schedules
        )  # Raw data
        assert all(schedule[1] == "<html>test</html>" for schedule in schedules)  # HTML
        assert mock_extract.call_count == 3


@pytest.mark.asyncio
async def test_crawl_schedules_integration():
    """Test the main crawl_schedules function"""
    from src.schedule.crawler import crawl_schedules

    with patch("src.schedule.crawler.ScheduleCrawler") as MockScheduleCrawler:
        # Configure crawler
        mock_crawler = AsyncMock()
        mock_crawler.get_schedules = AsyncMock(
            return_value=[
                ({"data": "week1"}, "<html>1</html>"),
                ({"data": "week2"}, "<html>2</html>"),
                ({"data": "week3"}, "<html>3</html>"),
            ]
        )
        MockScheduleCrawler.return_value = mock_crawler

        # Test crawl_schedules
        schedules = await crawl_schedules(
            "test@example.com", "password", "test_student"
        )

        assert len(schedules) == 3
        assert all(isinstance(schedule, tuple) for schedule in schedules)
        MockScheduleCrawler.assert_called_once_with(
            "test@example.com", "password", "test_student"
        )
        mock_crawler.get_schedules.assert_called_once()
