import pytest
from src.schedule.preprocessors.announcements import (
    parse_single_announcement,
    preprocess_announcements,
)
from src.schedule.preprocessors.exceptions import PreprocessingError


def test_parse_single_announcement():
    """Test parsing of individual announcements"""
    # Test valid cases
    text = "Centīgs: kārtīgi izpildīts mājas darbs (pozitīvs) (13.11., Mazākumtautību valoda un literatūra (krievu), Petroviča Tatjana)"
    result = parse_single_announcement(text)
    assert result["behavior_type"] == "Centīgs"
    assert result["description"] == "kārtīgi izpildīts mājas darbs"
    assert result["rating"] == "pozitīvs"
    assert result["subject"] == "Mazākumtautību valoda un literatūra (krievu)"

    text = "Mērķtiecīgs: aktīvs darbs stundā (pozitīvs) (15.11., Sociālās zinības, Demida Ludmila)"
    result = parse_single_announcement(text)
    assert result["behavior_type"] == "Mērķtiecīgs"
    assert result["description"] == "aktīvs darbs stundā"
    assert result["rating"] == "pozitīvs"
    assert result["subject"] == "Sociālās zinības"

    # Test invalid cases
    with pytest.raises(PreprocessingError) as exc:
        parse_single_announcement("Invalid announcement")
    assert "Invalid announcement format" in str(exc.value)


def test_preprocess_announcements():
    """Test preprocessing of announcements in schedule data"""
    input_data = [
        {
            "date": "13.11.24",
            "announcements": [
                {
                    "text": "Centīgs: kārtīgi izpildīts mājas darbs (pozitīvs) (13.11., Mazākumtautību valoda un literatūra (krievu), Petroviča Tatjana)"
                },
                {
                    "text": "Mērķtiecīgs: aktīvs darbs stundā (pozitīvs) (15.11., Sociālās zinības, Demida Ludmila)"
                },
            ],
        }
    ]

    processed = preprocess_announcements(input_data)
    announcements = processed[0]["announcements"]

    assert len(announcements) == 2
    assert announcements[0]["behavior_type"] == "Centīgs"
    assert announcements[0]["subject"] == "Mazākumtautību valoda un literatūra (krievu)"
    assert announcements[1]["behavior_type"] == "Mērķtiecīgs"
    assert announcements[1]["subject"] == "Sociālās zinības"

    # Test with invalid data
    invalid_data = [
        {"date": "13.11.24", "announcements": [{"text": "Invalid announcement"}]}
    ]

    with pytest.raises(PreprocessingError) as exc:
        preprocess_announcements(invalid_data)
    assert "Failed to process announcement" in str(exc.value)


def test_announcements_edge_cases():
    """Test edge cases in announcement processing"""
    # Test empty announcements list
    data = [{"date": "13.11.24", "announcements": []}]
    processed = preprocess_announcements(data)
    assert processed[0]["announcements"] == []

    # Test missing announcements key
    data = [{"date": "13.11.24"}]
    processed = preprocess_announcements(data)
    assert "announcements" not in processed[0]

    # Test invalid announcement structure
    data = [
        {
            "date": "13.11.24",
            "announcements": [{"wrong_key": "some text"}],  # Missing "text" key
        }
    ]
    with pytest.raises(PreprocessingError) as exc:
        preprocess_announcements(data)
    assert "Invalid announcement data structure" in str(exc.value)
