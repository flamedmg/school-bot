"""
Tests for the attachments preprocessor
"""

from datetime import datetime

import pytest

from src.schedule.preprocessors.attachments import (
    clean_lesson_number,
    extract_attachments,
    generate_unique_id,
)
from src.schedule.preprocessors.exceptions import PreprocessingError


def test_clean_lesson_number():
    """Test lesson number cleaning function"""
    assert clean_lesson_number("1. ") == "1"
    assert clean_lesson_number("2.") == "2"
    assert clean_lesson_number("10") == "10"
    assert clean_lesson_number("") == "0"
    assert clean_lesson_number(". ") == "0"
    assert clean_lesson_number("abc") == "0"
    assert clean_lesson_number("1.2.3") == "123"
    assert clean_lesson_number("5th") == "5"


def test_generate_unique_id():
    """Test unique ID generation"""
    unique_id = generate_unique_id("202401", "Math Class", "1", "20240101")
    assert unique_id == "202401_20240101_math_class_1"

    # Test with spaces and special characters
    unique_id = generate_unique_id("202401", "Math & Science!", "2", "20240101")
    assert unique_id == "202401_20240101_math_science_2"


def test_extract_attachments_empty_data():
    """Test extraction with empty data"""
    data = []
    result = extract_attachments(data)
    assert isinstance(result, list)
    assert len(result) == 1
    assert "attachments" in result[0]
    assert result[0]["attachments"] == []


def test_extract_attachments_no_homework():
    """Test extraction when there's no homework"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [{"subject": "Math", "number": "1. "}],
                }
            ]
        }
    ]
    result = extract_attachments(data)
    assert "attachments" in result[0]
    assert result[0]["attachments"] == []


def test_extract_attachments_with_base_url():
    """Test extraction with base_url parameter"""
    test_date = datetime(2024, 1, 1)
    data = [
        {
            "days": [
                {
                    "date": test_date,
                    "lessons": [
                        {
                            "subject": "Math",
                            "number": "1. ",
                            "homework": {
                                "text": "Do exercises",
                                "attachments": [
                                    {
                                        "filename": "math1.pdf",
                                        "url": "/files/math1.pdf",
                                    }
                                ],
                            },
                        }
                    ],
                }
            ]
        }
    ]

    base_url = "https://example.com"
    result = extract_attachments(data, base_url)

    assert "attachments" in result[0]
    attachments = result[0]["attachments"]
    assert len(attachments) == 1

    # Check that URL is properly joined with base_url
    assert attachments[0]["url"] == "https://example.com/files/math1.pdf"
    assert attachments[0]["unique_id"] == "202401_20240101_math_1"


def test_extract_attachments_with_attachments():
    """Test extraction with actual attachments"""
    test_date = datetime(2024, 1, 1)
    data = [
        {
            "days": [
                {
                    "date": test_date,
                    "lessons": [
                        {
                            "subject": "Math",
                            "number": "1. ",
                            "homework": {
                                "text": "Do exercises",
                                "attachments": [
                                    {
                                        "filename": "math1.pdf",
                                        "url": "/files/math1.pdf",
                                    },
                                    {
                                        "filename": "math2.pdf",
                                        "url": "/files/math2.pdf",
                                    },
                                ],
                            },
                        }
                    ],
                }
            ]
        }
    ]

    result = extract_attachments(data)

    assert "attachments" in result[0]
    attachments = result[0]["attachments"]
    assert len(attachments) == 2

    # Check first attachment
    assert attachments[0] == {
        "filename": "math1.pdf",
        "url": "/files/math1.pdf",
        "unique_id": "202401_20240101_math_1",
    }

    # Check second attachment
    assert attachments[1] == {
        "filename": "math2.pdf",
        "url": "/files/math2.pdf",
        "unique_id": "202401_20240101_math_1",
    }


def test_extract_attachments_multiple_days():
    """Test extraction from multiple days"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "subject": "Math",
                            "number": "1. ",
                            "homework": {
                                "attachments": [
                                    {"filename": "day1.pdf", "url": "/files/day1.pdf"}
                                ]
                            },
                        }
                    ],
                },
                {
                    "date": datetime(2024, 1, 2),
                    "lessons": [
                        {
                            "subject": "English",
                            "number": "2. ",
                            "homework": {
                                "attachments": [
                                    {"filename": "day2.pdf", "url": "/files/day2.pdf"}
                                ]
                            },
                        }
                    ],
                },
            ]
        }
    ]

    result = extract_attachments(data)
    attachments = result[0]["attachments"]

    assert len(attachments) == 2

    # Check first attachment
    assert attachments[0] == {
        "filename": "day1.pdf",
        "url": "/files/day1.pdf",
        "unique_id": "202401_20240101_math_1",
    }

    # Check second attachment
    assert attachments[1] == {
        "filename": "day2.pdf",
        "url": "/files/day2.pdf",
        "unique_id": "202401_20240102_english_2",
    }


def test_extract_attachments_invalid_data():
    """Test handling of invalid data"""
    invalid_data = [{"days": [{"lessons": "not a list"}]}]

    with pytest.raises(PreprocessingError) as exc_info:
        extract_attachments(invalid_data)

    assert "Failed to extract attachments" in str(exc_info.value)


def test_extract_attachments_direct_days_list():
    """Test extraction when input is direct list of days"""
    test_date = datetime(2024, 1, 1)
    data = [
        {
            "date": test_date,
            "lessons": [
                {
                    "subject": "Math",
                    "number": "1. ",
                    "homework": {
                        "attachments": [
                            {"filename": "test.pdf", "url": "/files/test.pdf"}
                        ]
                    },
                }
            ],
        }
    ]

    result = extract_attachments(data)
    assert len(result) == 1
    assert "attachments" in result[0]
    attachments = result[0]["attachments"]

    assert len(attachments) == 1
    # For direct days list, schedule_id is empty
    assert attachments[0] == {
        "filename": "test.pdf",
        "url": "/files/test.pdf",
        "unique_id": "_20240101_math_1",  # Empty schedule_id
    }


def test_extract_attachments_missing_filename():
    """Test handling of attachments with missing filename"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "subject": "Math",
                            "number": "1. ",
                            "homework": {
                                "attachments": [
                                    {
                                        # Missing filename
                                        "url": "/files/test.pdf"
                                    }
                                ]
                            },
                        }
                    ],
                }
            ]
        }
    ]

    result = extract_attachments(data)
    attachments = result[0]["attachments"]

    assert len(attachments) == 1
    assert attachments[0] == {
        "filename": "test.pdf",  # Extracted from URL
        "url": "/files/test.pdf",
        "unique_id": "202401_20240101_math_1",
    }


def test_extract_attachments_complex_urls():
    """Test filename extraction from various URL formats"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "subject": "Science",
                            "number": "1. ",
                            "homework": {
                                "attachments": [
                                    {"url": "/download?filename=test.pdf"},
                                    {"url": "/files/path/no-extension"},
                                    {"url": "https://example.com/file.doc?token=123"},
                                    {"url": "/complex/path"},
                                ]
                            },
                        }
                    ],
                }
            ]
        }
    ]

    result = extract_attachments(data)
    attachments = result[0]["attachments"]

    assert len(attachments) == 4

    # All attachments should have the same unique_id
    expected_unique_id = "202401_20240101_science_1"

    assert attachments[0] == {
        "filename": "test.pdf",
        "url": "/download?filename=test.pdf",
        "unique_id": expected_unique_id,
    }
    assert attachments[1] == {
        "filename": "no-extension",
        "url": "/files/path/no-extension",
        "unique_id": expected_unique_id,
    }
    assert attachments[2] == {
        "filename": "file.doc",
        "url": "https://example.com/file.doc?token=123",
        "unique_id": expected_unique_id,
    }
    assert attachments[3] == {
        "filename": "path",
        "url": "/complex/path",
        "unique_id": expected_unique_id,
    }


def test_extract_attachments_preserves_original_data():
    """Test that the original data structure is preserved"""
    original_data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "subject": "Math",
                            "number": "1. ",
                            "homework": {
                                "text": "Original homework",
                                "attachments": [
                                    {"filename": "test.pdf", "url": "/files/test.pdf"}
                                ],
                            },
                        }
                    ],
                }
            ]
        }
    ]

    result = extract_attachments(original_data)

    # Check that original homework data is preserved
    assert result[0]["days"][0]["lessons"][0]["homework"]["text"] == "Original homework"
    assert len(result[0]["days"][0]["lessons"][0]["homework"]["attachments"]) == 1

    # Check that attachment metadata is properly added
    attachments = result[0]["attachments"]
    assert len(attachments) == 1
    assert attachments[0] == {
        "filename": "test.pdf",
        "url": "/files/test.pdf",
        "unique_id": "202401_20240101_math_1",
    }


def test_extract_attachments_missing_number():
    """Test handling of lessons with missing number field"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "subject": "Math",
                            # No number field
                            "homework": {
                                "attachments": [
                                    {"filename": "test.pdf", "url": "/files/test.pdf"}
                                ]
                            },
                        }
                    ],
                }
            ]
        }
    ]

    result = extract_attachments(data)
    attachments = result[0]["attachments"]

    assert len(attachments) == 1
    assert (
        attachments[0]["unique_id"] == "202401_20240101_math_0"
    )  # Default lesson number


def test_extract_attachments_invalid_number_format():
    """Test handling of lessons with invalid number format"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "subject": "Math",
                            "number": "invalid",  # Invalid format
                            "homework": {
                                "attachments": [
                                    {"filename": "test.pdf", "url": "/files/test.pdf"}
                                ]
                            },
                        }
                    ],
                }
            ]
        }
    ]

    result = extract_attachments(data)
    attachments = result[0]["attachments"]

    assert len(attachments) == 1
    assert (
        attachments[0]["unique_id"] == "202401_20240101_math_0"
    )  # Default for invalid format
