from pathlib import Path

from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from src.schedule.crawler import JSON_SCHEMA
from src.schedule.preprocess import create_default_pipeline
from src.schedule.schema import Schedule

from .utils import load_test_file


def test_schedule_crawl():
    """Test the crawling of schedule data from HTML"""
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
    html = load_test_file("schedule_test1_full.html", base_dir="test_data")
    result = strategy.extract(html=html, url="https://test.com")

    # Print the result with explicit UTF-8 encoding
    # print("\n=== Extracted Schedule Data (UTF-8) ===\n", file=sys.stderr)
    # json_str = json.dumps(result, ensure_ascii=False, indent=2)
    # print(json_str, file=sys.stderr)
    # print("\n=====================================\n", file=sys.stderr)

    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0
    assert "days" in result[0]

    # Test structure of extracted data
    days = result[0]["days"]
    assert len(days) > 0

    # Test a sample day's structure
    sample_day = days[0]
    assert "date" in sample_day
    assert "lessons" in sample_day

    # Test lesson structure if present
    if sample_day["lessons"]:
        lesson = sample_day["lessons"][0]
        assert "number" in lesson
        assert "subject" in lesson
        assert "room" in lesson
        assert isinstance(lesson.get("homework", {}), dict | None)


def test_schedule_pipeline_output(capsys):
    """Test full pipeline processing and save output for comparison"""
    # Extract data using strategy
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
    html = load_test_file("schedule_test1_full.html", base_dir="test_data")
    raw_data = strategy.extract(html=html, url="https://test.com")

    # Create pipeline with markdown output
    output_dir = Path(__file__).parent / "test_data"
    pipeline = create_default_pipeline(
        markdown_output_path=output_dir / "schedule_processed.md"
    )

    # Execute pipeline without capturing output
    with capsys.disabled():
        print("\nExecuting pipeline steps:")
        final_data = pipeline.execute(raw_data)

    # Basic validation
    assert final_data is not None
    assert isinstance(final_data, list)
    assert len(final_data) > 0
    assert "days" in final_data[0]


def test_err20241128_schedule_parsing():
    """Test parsing of the err_schedule_20241128.html file"""
    strategy = JsonCssExtractionStrategy(JSON_SCHEMA)
    html = load_test_file("err_schedule_20241128.html", base_dir="test_data")
    result = strategy.extract(html=html, url="https://test.com")

    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0
    assert "days" in result[0]

    # Test structure of extracted data
    days = result[0]["days"]
    assert len(days) > 0

    # Test a sample day's structure
    sample_day = days[0]
    assert "date" in sample_day
    assert "lessons" in sample_day

    # Test lesson structure if present
    if sample_day["lessons"]:
        lesson = sample_day["lessons"][0]
        assert "number" in lesson
        assert "subject" in lesson
        assert "room" in lesson
        assert isinstance(lesson.get("homework", {}), dict | None)
    pipeline = create_default_pipeline(nickname="test")
    final_data = pipeline.execute(result)
    assert final_data is not None
    assert isinstance(final_data, list)
    assert len(final_data) > 0
    assert "days" in final_data[0]

    initial_schedule = Schedule(**final_data[0])
    assert initial_schedule is not None
    assert len(initial_schedule.days) > 0
