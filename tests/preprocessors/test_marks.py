import pytest

from src.schedule.preprocessors.exceptions import MarkPreprocessingError
from src.schedule.preprocessors.marks import (
    calculate_average_mark,
    convert_single_mark,
    preprocess_marks,
)


def test_convert_single_mark():
    """Test conversion of individual marks to 1-10 scale"""
    # Test valid cases
    assert convert_single_mark("85%") == 9
    assert convert_single_mark("100%") == 10
    assert convert_single_mark("45%") == 5
    assert convert_single_mark("S") == 3
    assert convert_single_mark("T") == 5
    assert convert_single_mark("A") == 7
    assert convert_single_mark("P") == 10
    assert convert_single_mark("NC") is None
    assert convert_single_mark("7") == 7

    # Test invalid cases
    with pytest.raises(MarkPreprocessingError) as exc:
        convert_single_mark("invalid")
    assert "Unable to convert mark" in str(exc.value)

    with pytest.raises(MarkPreprocessingError) as exc:
        convert_single_mark("")
    assert "Unable to convert mark" in str(exc.value)

    with pytest.raises(MarkPreprocessingError) as exc:
        convert_single_mark("11")  # Outside valid range
    assert "outside valid range" in str(exc.value)

    # Test non-string input
    assert convert_single_mark(123) is None
    assert convert_single_mark(None) is None
    assert convert_single_mark({}) is None


def test_calculate_average_mark():
    """Test calculation of average marks"""
    # Test valid cases
    assert (
        calculate_average_mark(["85%", "A", "P"]) == 9
    )  # (9 + 7 + 10) / 3 = 8.67 -> 9
    assert calculate_average_mark(["7", "NC", "8"]) == 8  # (7 + 8) / 2 = 7.5 -> 8
    assert calculate_average_mark(["NC", "NC"]) is None
    assert calculate_average_mark([]) is None

    # Test invalid cases
    with pytest.raises(MarkPreprocessingError) as exc:
        calculate_average_mark(["invalid", "85%"])
    assert "Unable to convert mark" in str(exc.value)

    with pytest.raises(MarkPreprocessingError) as exc:
        calculate_average_mark(["11", "85%"])
    assert "outside valid range" in str(exc.value)

    # Test non-list input
    assert calculate_average_mark(None) is None
    assert calculate_average_mark(123) is None
    assert calculate_average_mark("not a list") is None
    assert calculate_average_mark({}) is None


def test_preprocess_marks():
    """Test preprocessing of marks in schedule data"""
    # Test valid data
    input_data = [
        {
            "date": "2024-01-01",
            "lessons": [
                {
                    "subject": "Math",
                    "mark": [{"score": "85%"}, {"score": "A"}, {"score": "P"}],
                },
                {"subject": "English", "mark": [{"score": "NC"}]},
                {
                    "subject": "Science",
                    # No marks
                },
            ],
        }
    ]

    processed = preprocess_marks(input_data)
    assert (
        processed[0]["lessons"][0]["mark"] == 9
    )  # Now expecting integer instead of dict
    assert "mark" not in processed[0]["lessons"][1]  # NC marks should be removed
    assert "mark" not in processed[0]["lessons"][2]

    # Test invalid data
    invalid_data = [
        {
            "date": "2024-01-01",
            "lessons": [
                {"subject": "Math", "mark": [{"score": "invalid"}, {"score": "85%"}]}
            ],
        }
    ]

    with pytest.raises(MarkPreprocessingError) as exc:
        preprocess_marks(invalid_data)
    assert "Failed to process marks for lesson Math" in str(exc.value)
    assert "invalid" in str(exc.value.invalid_data)

    # Test invalid input types
    assert preprocess_marks(None) is None
    assert preprocess_marks(123) == 123
    assert preprocess_marks("not a list") == "not a list"

    # Test invalid days structure
    assert preprocess_marks([123, 456]) == [123, 456]
    assert preprocess_marks([{"no_days_key": []}]) == [{"no_days_key": []}]
    assert preprocess_marks([{"days": "not a list"}]) == [{"days": "not a list"}]

    # Test invalid lessons structure
    input_with_invalid_lessons = [
        {
            "date": "2024-01-01",
            "lessons": "not a list",
        }
    ]
    processed = preprocess_marks(input_with_invalid_lessons)
    assert processed == input_with_invalid_lessons

    # Test invalid marks structure
    input_with_invalid_marks = [
        {
            "date": "2024-01-01",
            "lessons": [
                {
                    "subject": "Math",
                    "mark": "not a list",  # Invalid marks type
                }
            ],
        }
    ]
    processed = preprocess_marks(input_with_invalid_marks)
    assert "mark" not in processed[0]["lessons"][0]


def test_error_context():
    """Test that error messages include proper context"""
    context = {
        "day_index": 0,
        "lesson_index": 1,
        "subject": "Math",
        "date": "2024-01-01",
    }

    with pytest.raises(MarkPreprocessingError) as exc:
        convert_single_mark("invalid", context)

    error_data = exc.value.invalid_data
    assert error_data["mark"] == "invalid"
    assert error_data["context"]["subject"] == "Math"
    assert error_data["context"]["date"] == "2024-01-01"


def test_wrapped_data_structure():
    """Test handling of wrapped data structure with 'days' key"""
    input_data = [
        {
            "days": [
                {
                    "date": "2024-01-01",
                    "lessons": [
                        {
                            "subject": "Math",
                            "mark": [{"score": "85%"}, {"score": "A"}],
                        }
                    ],
                }
            ]
        }
    ]

    processed = preprocess_marks(input_data)
    assert isinstance(processed, list)
    assert len(processed) == 1
    assert "days" in processed[0]
    assert processed[0]["days"][0]["lessons"][0]["mark"] == 8  # (9 + 7) / 2 = 8
