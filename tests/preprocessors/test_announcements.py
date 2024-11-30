import pytest

from src.schedule.preprocessors.announcements import (
    parse_single_announcement,
    preprocess_announcements,
)
from src.schedule.preprocessors.exceptions import PreprocessingError


def test_parse_single_announcement():
    """Test parsing of individual announcements"""
    # Test behavior announcement
    text = (
        "Centīgs: kārtīgi izpildīts mājas darbs (pozitīvs) "
        "(13.11., Mazākumtautību valoda un literatūra (krievu), "
        "Petroviča Tatjana)"
    )
    result = parse_single_announcement(text)
    assert result["type"] == "behavior"
    assert result["behavior_type"] == "Centīgs"
    assert result["description"] == "kārtīgi izpildīts mājas darbs"
    assert result["rating"] == "pozitīvs"
    assert result["subject"] == "Mazākumtautību valoda un literatūra (krievu)"

    # Test another behavior announcement
    text = (
        "Mērķtiecīgs: aktīvs darbs stundā (pozitīvs) "
        "(15.11., Sociālās zinības, Demida Ludmila)"
    )
    result = parse_single_announcement(text)
    assert result["type"] == "behavior"
    assert result["behavior_type"] == "Mērķtiecīgs"
    assert result["description"] == "aktīvs darbs stundā"
    assert result["rating"] == "pozitīvs"
    assert result["subject"] == "Sociālās zinības"

    # Test general announcement with date prefix
    text = "13.11. Skolas pasākums notiks sporta zālē"
    result = parse_single_announcement(text)
    assert result["type"] == "general"
    assert result["text"] == text

    # Test general announcement without date prefix
    text = (
        "Aicinu uz datorikas konsultāciju, ceturtdienā (21.11.), "
        "plkst. 12:35, 212. kab."
    )
    result = parse_single_announcement(text)
    assert result["type"] == "general"
    assert result["text"] == text


def test_preprocess_announcements():
    """Test preprocessing of announcements in schedule data"""
    input_data = [
        {
            "date": "13.11.24",
            "announcements": [
                {
                    "text": (
                        "Centīgs: kārtīgi izpildīts mājas darbs (pozitīvs) "
                        "(13.11., Mazākumtautību valoda un literatūra (krievu), "
                        "Petroviča Tatjana)"
                    )
                },
                {
                    "text": (
                        "Mērķtiecīgs: aktīvs darbs stundā (pozitīvs) "
                        "(15.11., Sociālās zinības, Demida Ludmila)"
                    )
                },
                {
                    "text": (
                        "Aicinu uz datorikas konsultāciju, ceturtdienā (21.11.), "
                        "plkst. 12:35, 212. kab."
                    )
                },
            ],
        }
    ]

    processed = preprocess_announcements(input_data)
    announcements = processed[0]["announcements"]

    assert len(announcements) == 3
    # Check behavior announcements
    assert announcements[0]["type"] == "behavior"
    assert announcements[0]["behavior_type"] == "Centīgs"
    assert announcements[0]["subject"] == "Mazākumtautību valoda un literatūra (krievu)"
    assert announcements[1]["type"] == "behavior"
    assert announcements[1]["behavior_type"] == "Mērķtiecīgs"
    assert announcements[1]["subject"] == "Sociālās zinības"
    # Check general announcement
    assert announcements[2]["type"] == "general"
    assert "Aicinu uz datorikas konsultāciju" in announcements[2]["text"]


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
