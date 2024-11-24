import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from crawl4ai import AsyncWebCrawler
from src.crawler.schedule.crawler import ScheduleCrawler, crawl_schedules

@pytest.fixture
def mock_cookies():
    return [
        {"name": "sessionId", "value": "test123", "domain": ".e-klase.lv"},
        {"name": "userId", "value": "user123", "domain": ".e-klase.lv"}
    ]

@pytest.fixture
def mock_html():
    return """
    <html>
        <body>
            <div class="schedule-table">
                <div class="lesson">Test Lesson</div>
            </div>
        </body>
    </html>
    """

@pytest.mark.asyncio
async def test_login_success(mock_cookies):
    """Test successful login and cookie retrieval"""
    with patch('crawl4ai.AsyncWebCrawler', autospec=True) as MockCrawler:
        # Setup mock crawler
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.cookies.return_value = mock_cookies
        mock_context.new_page.return_value = mock_page
        
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.strategy.context = mock_context
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Create crawler and test login
        crawler = ScheduleCrawler("test@example.com", "password")
        cookies = await crawler.login()

        # Verify login flow
        assert mock_page.goto.called_with(crawler.LOGIN_URL)
        assert mock_page.fill.call_count == 2  # Username and password
        assert mock_page.click.called
        assert mock_page.wait_for_navigation.called
        
        # Verify cookies
        assert cookies == mock_cookies

@pytest.mark.asyncio
async def test_login_failure():
    """Test login failure handling"""
    with patch('crawl4ai.AsyncWebCrawler', autospec=True) as MockCrawler:
        # Setup mock crawler with error element
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = MagicMock()  # Error element exists
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.strategy.context = mock_context
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Test login failure
        crawler = ScheduleCrawler("test@example.com", "wrong_password")
        with pytest.raises(Exception, match="Login failed"):
            await crawler.login()

@pytest.mark.asyncio
async def test_get_schedule_for_week(mock_cookies, mock_html):
    """Test fetching schedule for a specific week"""
    with patch('crawl4ai.AsyncWebCrawler', autospec=True) as MockCrawler:
        # Setup mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.get_html.return_value = mock_html
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Create crawler and set cookies
        crawler = ScheduleCrawler("test@example.com", "password")
        crawler.cookies = mock_cookies

        # Test getting schedule
        date = datetime.now()
        schedule = await crawler.get_schedule_for_week(date)

        # Verify schedule fetching
        assert schedule == mock_html
        assert MockCrawler.called_with(cookies=mock_cookies)

@pytest.mark.asyncio
async def test_get_schedules(mock_cookies, mock_html):
    """Test fetching schedules for all three weeks"""
    with patch('crawl4ai.AsyncWebCrawler', autospec=True) as MockCrawler:
        # Setup mock crawler
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.get_html.return_value = mock_html
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
        assert all(schedule == mock_html for schedule in schedules)
        assert mock_login.called_once()  # Login called once
        assert MockCrawler.call_count == 3  # Called for each week

@pytest.mark.asyncio
async def test_crawl_schedules_integration():
    """Test the main crawl_schedules function"""
    with patch('src.crawler.schedule.crawler.ScheduleCrawler') as MockScheduleCrawler:
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
