import pytest
from src.schedule.preprocessors.translation import Translator, preprocess_translations
from src.schedule.preprocessors.exceptions import PreprocessingError


def test_translator_initialization():
    """Test that translator loads successfully"""
    translator = Translator()
    assert translator.translations is not None
    assert "subjects" in translator.translations


def test_subject_translation():
    """Test translation of individual subjects"""
    translator = Translator()

    # Test known translations
    assert translator.translate_subject("Matemātika") == "Math"
    assert translator.translate_subject("Latviešu valoda un literatūra") == "Latvian"

    # Test unknown subject returns original
    assert translator.translate_subject("Unknown Subject") == "Unknown Subject"

    # Test empty/None cases
    assert translator.translate_subject("") == ""
    assert translator.translate_subject(None) == None


def test_preprocess_translations():
    """Test translation preprocessing of schedule data"""
    input_data = [
        {
            "days": [
                {
                    "date": "2024-03-23",
                    "lessons": [
                        {"subject": "Matemātika210", "room": "210"},
                        {"subject": "Latviešu valoda un literatūra403", "room": "403"},
                        {"subject": "Unknown Subject101", "room": "101"},
                    ],
                }
            ]
        }
    ]

    processed = preprocess_translations(input_data)

    # Verify translations
    lessons = processed[0]["days"][0]["lessons"]
    assert lessons[0]["subject"] == "Math"
    assert lessons[1]["subject"] == "Latvian"
    assert lessons[2]["subject"] == "Unknown Subject"  # Unchanged


def test_preprocess_translations_error_handling():
    """Test error handling in translation preprocessing"""
    # Test with invalid data structure
    invalid_data = [{"invalid": "structure"}]

    # Should not raise error, just return data unchanged
    result = preprocess_translations(invalid_data)
    assert result == invalid_data

    # Test with None values
    data_with_none = [{"days": [{"lessons": [{"subject": None}]}]}]
    result = preprocess_translations(data_with_none)
    assert result[0]["days"][0]["lessons"][0]["subject"] == None
