import pytest
from src.schedule.preprocessors.marks import (
    convert_single_mark,
    calculate_average_mark,
    preprocess_marks,
)
from src.schedule.preprocessors.exceptions import MarkPreprocessingError


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
