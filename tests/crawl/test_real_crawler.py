import os
import pytest
from datetime import datetime
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from src.crawler.schedule.crawler import ScheduleCrawler, crawl_schedules
from src.crawler.schedule.schedule import schema

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
"""

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
    
    return {
        "email": email,
        "password": password
    }

# @pytest.mark.realtest
@pytest.mark.asyncio
async def test_real_login(credentials):
    """Test real login to e-klasse"""
    crawler = ScheduleCrawler(credentials["email"], credentials["password"])
    
    try:
        cookies = await crawler.login()
        assert cookies is not None
        assert len(cookies) > 0
        assert any(cookie.get("domain", "").endswith("e-klase.lv") for cookie in cookies)
        
        print("\nSuccessfully logged in and retrieved cookies:")
        for cookie in cookies:
            print(f"- {cookie.get('name')}: domain={cookie.get('domain')}")
            
    except Exception as e:
        pytest.fail(f"Login failed: {str(e)}")

pytest.mark.realtest
@pytest.mark.asyncio
async def test_cookie_reuse(credentials):
    """Test that cookies are properly reused across requests"""
    crawler = ScheduleCrawler(credentials["email"], credentials["password"])
    
    try:
        # First request - should perform logi
        print("\nPerforming initial login...")
        cookies = await crawler.login()
        assert cookies is not None
        initial_cookie_count = len(cookies)
        
        # Store initial cookies for comparison
        initial_cookies = {cookie.get('name'): cookie.get('value') for cookie in cookies}
        
        # Second request - should reuse cookies
        print("\nFetching schedule with stored cookies...")
        current_date = datetime.now()
        schedule_html = await crawler.get_schedule_for_week(current_date)
        assert schedule_html is not None
        assert "licejs-my.sharepoint.com" in schedule_html
        
        # Verify cookies were reused and not regenerated
        print("\nVerifying cookie reuse...")
        current_cookies = crawler.cookies
        current_cookie_dict = {cookie.get('name'): cookie.get('value') for cookie in current_cookies}
        
        # Check that essential cookies are preserved
        for name, value in initial_cookies.items():
            if name in current_cookie_dict:
                assert current_cookie_dict[name] == value, f"Cookie {name} value changed"
        
        print(f"Successfully verified cookie reuse - {len(current_cookies)} cookies maintained")
            
    except Exception as e:
        pytest.fail(f"Cookie reuse test failed: {str(e)}")

@pytest.mark.realtest
@pytest.mark.asyncio
async def test_real_schedule_fetch(credentials):
    """Test fetching real schedules"""
    crawler = ScheduleCrawler(credentials["email"], credentials["password"])
    
    try:
        # Get current week schedule
        current_date = datetime.now()
        schedule_html = await crawler.get_schedule_for_week(current_date)
        
        assert schedule_html is not None
        assert "schedule-table" in schedule_html
        
        # Verify HTML structure using extraction strategy
        strategy = JsonCssExtractionStrategy(schema)
        raw_data = strategy.extract(html=schedule_html, url="https://www.e-klase.lv")
        
        assert raw_data is not None
        if isinstance(raw_data, list):
            assert len(raw_data) > 0
            schedule_data = raw_data[0]
            assert 'lessons' in schedule_data
            
            print("\nSuccessfully fetched and validated schedule:")
            print(f"- Number of lessons: {len(schedule_data['lessons'])}")
            for lesson in schedule_data['lessons'][:3]:  # Print first 3 lessons
                print(f"- Lesson: {lesson.get('subject')} (Room: {lesson.get('room')})")
                
    except Exception as e:
        pytest.fail(f"Schedule fetch failed: {str(e)}")

@pytest.mark.realtest
@pytest.mark.asyncio
async def test_real_three_weeks_fetch(credentials):
    """Test fetching three weeks of schedules"""
    try:
        schedules = await crawl_schedules(
            email=credentials["email"],
            password=credentials["password"]
        )
        
        assert schedules is not None
        assert len(schedules) == 3
        
        # Verify each schedule
        strategy = JsonCssExtractionStrategy(schema)
        for i, schedule_html in enumerate(schedules):
            raw_data = strategy.extract(html=schedule_html, url="https://www.e-klase.lv")
            assert raw_data is not None
            if isinstance(raw_data, list):
                assert len(raw_data) > 0
                schedule_data = raw_data[0]
                
                print(f"\nWeek {i+1} schedule:")
                print(f"- Number of lessons: {len(schedule_data['lessons'])}")
                if schedule_data['lessons']:
                    first_lesson = schedule_data['lessons'][0]
                    print(f"- First lesson: {first_lesson.get('subject')}")
                    
                # Print some homework if available
                for lesson in schedule_data['lessons']:
                    if lesson.get('homework'):
                        print(f"- Homework for {lesson.get('subject')}: {lesson['homework'].get('text', 'No text')}")
                        break
                
    except Exception as e:
        pytest.fail(f"Three weeks fetch failed: {str(e)}")
