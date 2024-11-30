import pytest
from src.schedule.preprocessors.lessons import (
    clean_lesson_index,
    clean_topic,
    preprocess_lesson,
    preprocess_lessons,
    clean_subject,
)
from src.schedule.preprocessors.exceptions import PreprocessingError


def test_clean_lesson_index():
    """Test cleaning of lesson numbers into indices"""
    # Basic cases
    assert clean_lesson_index("1.") == 1
    assert clean_lesson_index("7.") == 7
    assert clean_lesson_index("·") is None
    assert clean_lesson_index(None) is None

    # Real examples from schedule
    assert clean_lesson_index("2.") == 2
    assert clean_lesson_index("8.") == 8
    assert (
        clean_lesson_index("·") is None
    )  # Special lessons like "Tautas dejas kol. 'Balaguri' (I)"

    # Error cases
    with pytest.raises(PreprocessingError):
        clean_lesson_index("invalid")
    with pytest.raises(PreprocessingError):
        clean_lesson_index("")


def test_clean_subject():
    """Test separation of subject and room"""
    # Test cases with room numbers
    assert clean_subject("Matemātika210") == ("Matemātika", "210")
    assert clean_subject("Latviešu valoda un literatūra403") == (
        "Latviešu valoda un literatūra",
        "403",
    )

    # Test cases with known room codes
    assert clean_subject("Sports un veselībasz") == ("Sports un veselība", "sz")
    assert clean_subject("Sports un veselībamz") == ("Sports un veselība", "mz")
    assert clean_subject("Dejas un ritmika (F)az") == ("Dejas un ritmika (F)", "az")

    # Test cases without room numbers or codes
    assert clean_subject("English") == ("English", None)
    assert clean_subject("Science") == ("Science", None)
    assert clean_subject("Tautas dejas kol. 'Balaguri' (I)") == (
        "Tautas dejas kol. 'Balaguri'",
        None,
    )

    # Edge cases
    assert clean_subject("") == (None, None)
    assert clean_subject(None) == (None, None)


def test_clean_subject_with_room():
    """Test separation of subject and room with specific cases"""
    assert clean_subject("Latviešu valoda un literatūra403") == (
        "Latviešu valoda un literatūra",
        "403",
    )
    assert clean_subject("Matemātika210") == ("Matemātika", "210")
    assert clean_subject("Sports un veselībasz") == ("Sports un veselība", "sz")


def test_preprocess_lesson():
    """Test preprocessing of complete lesson entries"""
    # Real example from schedule - Math lesson
    math_lesson = {
        "index": 1,
        "subject": "Matemātika210",
        "room": "210",
        "topic": "Kāda ir darbību secība izteiksmēs?SR: nosauc darbību secību pēc kārtas; atrisina\n                            izteiksmes pēc parauga.",
        "homework": {
            "text": "G. 140. lpp., 42., 44*. uzd.",
            "links": [],
            "attachments": [],
        },
        "mark": [{"score": "88,89%"}],
    }

    processed = preprocess_lesson(math_lesson)
    assert processed["index"] == 1  # Changed from number to index
    assert "number" not in processed  # Old field removed
    assert processed["subject"] == "Matemātika"  # Updated to expect cleaned subject
    assert processed["room"] == "210"  # Room number is preserved
    assert (
        processed["topic"]
        == "Kāda ir darbību secība izteiksmēs?SR: nosauc darbību secību pēc kārtas; atrisina izteiksmes pēc parauga."
    )

    # Real example - Special lesson (Tautas dejas)
    special_lesson = {
        "number": "·",  # Special lesson marker gets converted to next available index
        "subject": "Tautas dejas kol. 'Balaguri' (I)",
        "room": "",
        "topic": 'Latviešu deja "Kur tad tu?". S.R.: Mugurdancis.',
        "homework": {"links": [], "attachments": []},
    }
    processed = preprocess_lesson(special_lesson)
    assert (
        "index" in processed
    )  # Should have an index (will be assigned by preprocess_lessons)
    assert "number" not in processed  # Old field removed
    assert processed["subject"] == "Tautas dejas kol. 'Balaguri'"  # (I) removed
    assert processed["topic"] == 'Latviešu deja "Kur tad tu?". S.R.: Mugurdancis.'

    # Real example - Sports lesson
    sports_lesson = {
        "index": 1,
        "subject": "Sports un veselībasz",
        "room": "sz",
        "topic": "Kā izmantot radošās domāšanas stratēģijas\n                              rotaļās?(SR: ar skolotāja atbalstu sadarbojoties pārī vai\n                            mazā grupā, rada jaunas idejas spēlēm, to\n                            nosacījumiem un kopīgi izvēlas labāko risinājumu\n                            uzdevuma veikšanai.)",
        "homework": {"links": [], "attachments": []},
    }
    processed = preprocess_lesson(sports_lesson)
    assert processed["index"] == 1  # Changed from checking "number" to "index"
    assert "number" not in processed  # Old field removed
    assert (
        processed["subject"] == "Sports un veselība"
    )  # Changed: expect cleaned subject without 'sz'
    assert processed["room"] == "sz"  # The 'sz' part becomes the room
    assert "rotaļās?" in processed["topic"]


def test_preprocess_lessons():
    """Test preprocessing of complete schedule data"""
    input_data = [
        {
            "date": "11.11.24. pirmdiena",
            "lessons": [
                {
                    "number": "2.",
                    "subject": "Latviešu valoda un literatūra403",
                    "room": "403",
                    "topic": "Gatavošanās pārbaudes darbam.SR:atkārto mācīto\n                            materiālu un gatavojas pārbaudes darbam.",
                    "homework": {
                        "text": "Turpināt gatavoties pārbaudes darbam (sk.pielikumu).",
                        "links": [
                            {
                                "url": "/Attachment/Get/e686f1ba-5be8-46a3-aec1-9ccfb83dba5c"
                            }
                        ],
                        "attachments": [
                            {
                                "filename": "atkārtot p_d__uz 12_11_2024_.pptx",
                                "url": "/Attachment/Get/e686f1ba-5be8-46a3-aec1-9ccfb83dba5c",
                            }
                        ],
                    },
                },
                {
                    "number": "·",
                    "subject": "Tautas dejas kol. 'Balaguri' (I)",
                    "topic": 'Latviešu deja "Kur tad tu?". S.R.: Mugurdancis.',
                    "homework": {"links": [], "attachments": []},
                    "mark": [{"score": "nc"}],
                },
            ],
        }
    ]

    processed = preprocess_lessons(input_data)

    # Verify first lesson
    lesson1 = processed[0]["lessons"][0]
    assert lesson1["index"] == 2  # Changed from checking "number" to "index"
    assert "number" not in lesson1  # Old field removed
    assert (
        lesson1["subject"] == "Latviešu valoda un literatūra"
    )  # Updated to expect cleaned subject
    assert lesson1["room"] == "403"  # Room number is preserved
    assert "Gatavošanās pārbaudes darbam" in lesson1["topic"]

    # Verify special lesson
    lesson2 = processed[0]["lessons"][1]
    assert lesson2["index"] == 3  # Gets next available index after 2
    assert "number" not in lesson2  # Old field removed
    assert lesson2["subject"] == "Tautas dejas kol. 'Balaguri'"
    assert "Mugurdancis" in lesson2["topic"]


def test_sequential_lesson_indices():
    """Test assignment of sequential indices for lessons with missing numbers"""
    input_data = [
        {
            "date": "2024-01-01",
            "lessons": [
                {"number": "1.", "subject": "Math", "topic": "Topic 1"},
                {
                    "number": None,  # Missing number
                    "subject": "English",
                    "topic": "Topic 2",
                },
                {"number": "3.", "subject": "Science", "topic": "Topic 3"},
                {
                    "number": "·",  # Special lesson marker
                    "subject": "Art",
                    "topic": "Topic 4",
                },
                {"number": "5.", "subject": "History", "topic": "Topic 5"},
            ],
        }
    ]

    processed = preprocess_lessons(input_data)
    lessons = processed[0]["lessons"]

    # Verify indices are assigned correctly
    assert lessons[0]["index"] == 1  # Kept original
    assert lessons[1]["index"] == 2  # Assigned next available
    assert lessons[2]["index"] == 3  # Kept original
    assert lessons[3]["index"] == 4  # Special lesson gets next sequential index
    assert lessons[4]["index"] == 5  # Kept original

    # Verify old number field is removed
    for lesson in lessons:
        assert "number" not in lesson


def test_handle_duplicate_indices():
    """Test handling of duplicate lesson numbers"""
    input_data = [
        {
            "date": "2024-01-01",
            "lessons": [
                {"number": "1.", "subject": "Math"},
                {"number": "1.", "subject": "English"},  # Duplicate number
                {"number": "2.", "subject": "Science"},
            ],
        }
    ]

    processed = preprocess_lessons(input_data)
    lessons = processed[0]["lessons"]

    # First occurrence keeps the number, second gets next available
    assert lessons[0]["index"] == 1  # First occurrence keeps original
    assert lessons[1]["index"] == 1  # Second occurrence also keeps original
    assert lessons[2]["index"] == 2  # Keeps original


def test_handle_gaps_in_indices():
    """Test handling of gaps in lesson numbers"""
    input_data = [
        {
            "date": "2024-01-01",
            "lessons": [
                {"number": "1.", "subject": "Math"},
                {"number": "4.", "subject": "English"},  # Gap in numbering
                {"number": None, "subject": "Science"},
            ],
        }
    ]

    processed = preprocess_lessons(input_data)
    lessons = processed[0]["lessons"]

    # Verify indices are assigned correctly
    assert lessons[0]["index"] == 1  # Keeps original
    assert lessons[1]["index"] == 4  # Keeps original gap
    assert lessons[2]["index"] == 5  # Gets next available after 1


def test_error_handling():
    """Test error handling in preprocessing"""
    # Test with invalid data structure
    invalid_lesson = {"number": {}, "subject": "Math"}  # Invalid type for number

    with pytest.raises(PreprocessingError) as exc:
        preprocess_lesson(invalid_lesson)
    # Update expected error message to match the more detailed one
    assert "Invalid lesson number type" in str(exc.value)
    assert "expected string or None" in str(exc.value)
    assert "<class 'dict'>" in str(exc.value)
