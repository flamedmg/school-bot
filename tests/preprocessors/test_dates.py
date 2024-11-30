from datetime import datetime

from src.schedule.preprocessors.dates import preprocess_dates_and_merge


def test_preprocess_dates_and_merge_basic():
    """Test basic date preprocessing with simple input"""
    input_days = [
        {"date": "11.11.24. pirmdiena", "lessons": [], "announcements": []},
        {
            "date": "Priekšmets un telpaTēmaUzdotsAtzīme",
            "lessons": [{"number": "1", "subject": "Math"}],
            "announcements": [],
        },
    ]

    result = preprocess_dates_and_merge(input_days)

    assert len(result) == 1
    assert isinstance(result[0]["date"], datetime)
    assert result[0]["date"].strftime("%d/%m/%Y") == "11/11/2024"
    assert len(result[0]["lessons"]) == 1


def test_preprocess_dates_and_merge_multiple_pairs():
    """Test preprocessing multiple day pairs"""
    input_days = [
        {"date": "11.11.24. pirmdiena", "lessons": [], "announcements": []},
        {"date": "garbage1", "lessons": [{"number": "1"}], "announcements": []},
        {"date": "12.11.24. otrdiena", "lessons": [], "announcements": []},
        {"date": "garbage2", "lessons": [{"number": "2"}], "announcements": []},
    ]

    result = preprocess_dates_and_merge(input_days)

    assert len(result) == 2
    assert isinstance(result[0]["date"], datetime)
    assert isinstance(result[1]["date"], datetime)
    assert result[0]["date"].strftime("%d/%m/%Y") == "11/11/2024"
    assert result[1]["date"].strftime("%d/%m/%Y") == "12/11/2024"


def test_preprocess_dates_and_merge_invalid_date():
    """Test handling of invalid date formats"""
    input_days = [
        {"date": "invalid date", "lessons": [], "announcements": []},
        {"date": "garbage", "lessons": [{"number": "1"}], "announcements": []},
    ]

    result = preprocess_dates_and_merge(input_days)

    assert len(result) == 2
    assert result[0]["date"] == "invalid date"  # Should preserve original if invalid
    assert result[1]["date"] == "garbage"


def test_basic_date_processing():
    """Test basic date processing with valid input"""
    input_data = [
        {
            "days": [
                {"date": "11.11.24. pirmdiena", "lessons": [], "announcements": []},
                {
                    "date": "Priekšmets un telpaTēmaUzdotsAtzīme",
                    "lessons": [{"subject": "Math"}],
                    "announcements": [],
                },
            ]
        }
    ]

    result = preprocess_dates_and_merge(input_data)
    assert len(result) == 1
    assert len(result[0]["days"]) == 1
    assert isinstance(result[0]["days"][0]["date"], datetime)
    assert result[0]["days"][0]["date"].day == 11
    assert result[0]["days"][0]["date"].month == 11
    assert result[0]["days"][0]["date"].year == 2024


def test_single_day_processing():
    """Test processing of single day entries"""
    input_data = [
        {
            "days": [
                {
                    "date": "11.11.24. pirmdiena",
                    "lessons": [{"subject": "Math"}],
                    "announcements": ["Test announcement"],
                }
            ]
        }
    ]

    result = preprocess_dates_and_merge(input_data)
    assert len(result) == 1
    assert len(result[0]["days"]) == 1
    assert result[0]["days"][0]["lessons"][0]["subject"] == "Math"
    assert result[0]["days"][0]["announcements"][0] == "Test announcement"


def test_multiple_day_pairs():
    """Test processing multiple day pairs"""
    input_data = [
        {
            "days": [
                # First pair
                {"date": "11.11.24. pirmdiena", "lessons": [], "announcements": []},
                {
                    "date": "Content1",
                    "lessons": [{"subject": "Math"}],
                    "announcements": [],
                },
                # Second pair
                {"date": "12.11.24. otrdiena", "lessons": [], "announcements": []},
                {
                    "date": "Content2",
                    "lessons": [{"subject": "English"}],
                    "announcements": [],
                },
            ]
        }
    ]

    result = preprocess_dates_and_merge(input_data)
    assert len(result) == 1
    assert len(result[0]["days"]) == 2

    # Check first day
    assert result[0]["days"][0]["date"].day == 11
    assert result[0]["days"][0]["lessons"][0]["subject"] == "Math"

    # Check second day
    assert result[0]["days"][1]["date"].day == 12
    assert result[0]["days"][1]["lessons"][0]["subject"] == "English"


def test_invalid_date_format():
    """Test handling of invalid date formats"""
    input_data = [
        {
            "days": [
                {"date": "invalid date", "lessons": [], "announcements": []},
                {
                    "date": "Content",
                    "lessons": [{"subject": "Math"}],
                    "announcements": [],
                },
            ]
        }
    ]

    result = preprocess_dates_and_merge(input_data)
    # Should preserve original entries when date parsing fails
    assert len(result) == 1
    assert len(result[0]["days"]) == 2
    assert result[0]["days"][0]["date"] == "invalid date"


def test_empty_input():
    """Test handling of empty input"""
    assert preprocess_dates_and_merge([]) == []
    assert preprocess_dates_and_merge(None) is None
    assert preprocess_dates_and_merge([{}]) == [{}]


def test_missing_days():
    """Test handling of entries without days"""
    input_data = [{"other_field": "value"}]
    result = preprocess_dates_and_merge(input_data)
    assert result == input_data


def test_malformed_input():
    """Test handling of malformed input"""
    # Test with non-list days
    input_data = [{"days": "not a list"}]
    result = preprocess_dates_and_merge(input_data)
    assert result == input_data

    # Test with non-dict day entries
    input_data = [{"days": ["not a dict"]}]
    result = preprocess_dates_and_merge(input_data)
    assert result == [{"days": ["not a dict"]}]


def test_real_world_example():
    """Test with a real-world example from the schedule"""
    input_data = [
        {
            "days": [
                {"date": "11.11.24. pirmdiena", "lessons": [], "announcements": []},
                {
                    "date": "Priekšmets un telpaTēmaUzdotsAtzīme",
                    "lessons": [
                        {
                            "number": "2.",
                            "subject": "Latviešu valoda un literatūra403",
                            "room": "403",
                            "topic": "Gatavošanās pārbaudes darbam.",
                            "homework": {"text": "Test homework"},
                        }
                    ],
                    "announcements": ["Test announcement"],
                },
            ]
        }
    ]

    result = preprocess_dates_and_merge(input_data)
    assert len(result) == 1
    assert len(result[0]["days"]) == 1

    processed_day = result[0]["days"][0]
    assert isinstance(processed_day["date"], datetime)
    assert processed_day["date"].strftime("%d.%m.%y") == "11.11.24"
    assert len(processed_day["lessons"]) == 1
    assert processed_day["lessons"][0]["subject"] == "Latviešu valoda un literatūra403"
