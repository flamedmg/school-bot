import pytest
from urllib.parse import unquote
from src.schedule.preprocessors.homework import (
    extract_destination_url,
    combine_homework_texts,
    preprocess_homework,
)
from src.schedule.preprocessors.exceptions import PreprocessingError


def test_extract_destination_url():
    """Test extraction of destination URLs from OAuth links"""
    # Test uzdevumi.lv OAuth link
    oauth_link = "/Auth/OAuth/RemoteApp?client_id=a85e2c10-fb73-420a-83e1-85446ff9ac13&profiles=False&destination_uri=https%3a%2f%2fwww.uzdevumi.lv%2fTestWork%2fInfo%2f4649268"
    result = extract_destination_url(oauth_link)
    assert result == {
        "original_url": oauth_link,
        "destination_url": "https://www.uzdevumi.lv/TestWork/Info/4649268",
    }

    # Test regular attachment link
    attachment_link = "/Attachment/Get/e686f1ba-5be8-46a3-aec1-9ccfb83dba5c"
    result = extract_destination_url(attachment_link)
    assert result == {
        "original_url": attachment_link,
        "destination_url": None,  # No destination URL for regular attachments
    }

    # Test regular external link
    external_link = "prezi.com/view/AenZE9InlMncuUlPQvAZ/"
    result = extract_destination_url(external_link)
    assert result == {
        "original_url": external_link,
        "destination_url": "https://prezi.com/view/AenZE9InlMncuUlPQvAZ/",
    }


def test_combine_homework_texts():
    """Test combining multiple homework text entries"""
    texts = [
        "G. 140. lpp., 42., 44*. uzd.",
        "Prezentācija stundai:",
        "Darba lapa. Kāda ir Latvijas valsts?",
    ]
    result = combine_homework_texts(texts)
    assert (
        result
        == "G. 140. lpp., 42., 44*. uzd. Prezentācija stundai: Darba lapa. Kāda ir Latvijas valsts?"
    )

    # Test empty list
    assert combine_homework_texts([]) is None

    # Test list with empty strings
    assert combine_homework_texts(["", "  ", ""]) is None


def test_preprocess_homework():
    """Test preprocessing of complete homework entries"""
    # Test case with all types of content
    homework_data = {
        "text": "Turpināt gatavoties pārbaudes darbam (sk.pielikumu).",
        "links": [
            {"url": "/Attachment/Get/e686f1ba-5be8-46a3-aec1-9ccfb83dba5c"},
            {
                "url": "/Auth/OAuth/RemoteApp?client_id=a85e2c10-fb73-420a-83e1-85446ff9ac13&profiles=False&destination_uri=https%3a%2f%2fwww.uzdevumi.lv%2fTestWork%2fInfo%2f4649268"
            },
        ],
        "attachments": [
            {
                "filename": "atkārtot p_d__uz 12_11_2024_.pptx",
                "url": "/Attachment/Get/e686f1ba-5be8-46a3-aec1-9ccfb83dba5c",
            }
        ],
    }

    result = preprocess_homework(homework_data)
    assert result["text"] == "Turpināt gatavoties pārbaudes darbam (sk.pielikumu)."
    assert len(result["links"]) == 1  # Duplicate link should be removed
    assert (
        result["links"][0]["destination_url"]
        == "https://www.uzdevumi.lv/TestWork/Info/4649268"
    )
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["filename"] == "atkārtot p_d__uz 12_11_2024_.pptx"

    # Test case with only text
    homework_data = {
        "text": "G. 140. lpp., 42., 44*. uzd.",
        "links": [],
        "attachments": [],
    }
    result = preprocess_homework(homework_data)
    assert result["text"] == "G. 140. lpp., 42., 44*. uzd."
    assert result["links"] == []
    assert result["attachments"] == []

    # Test case with multiple texts and links
    homework_data = {
        "text": "Prezentācija stundai:",
        "links": [{"url": "https://prezi.com/view/AenZE9InlMncuUlPQvAZ/"}],
        "attachments": [],
    }
    result = preprocess_homework(homework_data)
    assert "Prezentācija stundai:" in result["text"]
    assert len(result["links"]) == 1


def test_preprocess_homework_edge_cases():
    """Test edge cases in homework preprocessing"""
    # Empty homework
    assert preprocess_homework({}) == {"text": None, "links": [], "attachments": []}

    # Missing fields
    result = preprocess_homework({"text": "Some text"})
    assert result["text"] == "Some text"
    assert result["links"] == []
    assert result["attachments"] == []

    # Invalid link format
    with pytest.raises(PreprocessingError):
        preprocess_homework({"links": [{"url": "invalid-url"}]})


def test_real_examples():
    """Test with real examples from the schedule"""
    # Example 1: Math homework
    homework_data = {
        "text": "G. 140. lpp., 42., 44*. uzd.",
        "links": [],
        "attachments": [],
    }
    result = preprocess_homework(homework_data)
    assert result["text"] == "G. 140. lpp., 42., 44*. uzd."

    # Example 2: Homework with attachment
    homework_data = {
        "text": "Sagatavoties rakstīt pārbaudes darbu (sk.pielikumu).",
        "links": [{"url": "/Attachment/Get/1c0912a3-79f7-49aa-84a6-1caab219ef09"}],
        "attachments": [
            {
                "filename": "atkārtot p_d__uz 12_11_2024_.pptx",
                "url": "/Attachment/Get/1c0912a3-79f7-49aa-84a6-1caab219ef09",
            }
        ],
    }
    result = preprocess_homework(homework_data)
    assert "Sagatavoties rakstīt pārbaudes darbu" in result["text"]
    assert len(result["attachments"]) == 1
    assert "pptx" in result["attachments"][0]["filename"]
    assert len(result["links"]) == 0  # Duplicate link should be removed

    # Example 3: Homework with uzdevumi.lv link
    homework_data = {
        "links": [
            {
                "url": "/Auth/OAuth/RemoteApp?client_id=a85e2c10-fb73-420a-83e1-85446ff9ac13&profiles=False&destination_uri=https%3a%2f%2fwww.uzdevumi.lv%2fTestWork%2fInfo%2f4649268"
            }
        ],
        "attachments": [],
    }
    result = preprocess_homework(homework_data)
    assert len(result["links"]) == 1
    assert "uzdevumi.lv" in result["links"][0]["destination_url"]


def test_preprocess_homework_deduplication():
    """Test that duplicate URLs in links and attachments are removed"""
    homework_input = {
        "text": "Please complete the assignment.",
        "links": [
            {"url": "/Attachment/Get/duplicate-url"},
            {"url": "https://external-resource.com"},
        ],
        "attachments": [
            {"filename": "assignment.docx", "url": "/Attachment/Get/duplicate-url"}
        ],
    }

    expected_output = {
        "text": "Please complete the assignment.",
        "links": [
            {
                "original_url": "https://external-resource.com",
                "destination_url": "https://external-resource.com",
            }
        ],
        "attachments": [
            {"filename": "assignment.docx", "url": "/Attachment/Get/duplicate-url"}
        ],
    }

    result = preprocess_homework(homework_input)
    assert result["text"] == expected_output["text"]
    assert result["attachments"] == expected_output["attachments"]
    assert result["links"] == expected_output["links"]
