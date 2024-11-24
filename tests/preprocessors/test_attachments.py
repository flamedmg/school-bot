"""
Tests for the attachments preprocessor
"""

import pytest
from datetime import datetime
from src.schedule.preprocessors.attachments import extract_attachments
from src.schedule.preprocessors.exceptions import PreprocessingError


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
                    "lessons": [{"subject": "Math", "index": 1}],
                }
            ]
        }
    ]
    result = extract_attachments(data)
    assert "attachments" in result[0]
    assert result[0]["attachments"] == []


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
                            "index": 1,
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
    assert attachments[0] == {"filename": "math1.pdf", "url": "/files/math1.pdf"}

    # Check second attachment
    assert attachments[1] == {"filename": "math2.pdf", "url": "/files/math2.pdf"}


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
    assert attachments[0] == {"filename": "day1.pdf", "url": "/files/day1.pdf"}
    assert attachments[1] == {"filename": "day2.pdf", "url": "/files/day2.pdf"}


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
    assert attachments[0] == {"filename": "test.pdf", "url": "/files/test.pdf"}


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
    assert attachments[0]["filename"] == "test.pdf"
    assert attachments[0]["url"] == "/files/test.pdf"


def test_extract_attachments_complex_urls():
    """Test filename extraction from various URL formats"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "homework": {
                                "attachments": [
                                    {"url": "/download?filename=test.pdf"},
                                    {"url": "/files/path/no-extension"},
                                    {"url": "https://example.com/file.doc?token=123"},
                                    {"url": "/complex/path"},
                                ]
                            }
                        }
                    ],
                }
            ]
        }
    ]

    result = extract_attachments(data)
    attachments = result[0]["attachments"]

    assert len(attachments) == 4
    assert attachments[0]["filename"] == "test.pdf"
    assert attachments[1]["filename"] == "no-extension"
    assert attachments[2]["filename"] == "file.doc"
    assert attachments[3]["filename"] == "path"  # Filename extracted from the URL path


def test_extract_attachments_missing_fields():
    """Test handling of attachments with missing filename"""
    data = [
        {
            "days": [
                {
                    "date": datetime(2024, 1, 1),
                    "lessons": [
                        {
                            "subject": "Math",
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
    assert attachments[0]["filename"] == "test.pdf"
    assert attachments[0]["url"] == "/files/test.pdf"


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
