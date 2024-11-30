import pytest
from src.schedule.preprocessors.lessons import clean_subject


def test_subject_cleaning():
    """Test that subject cleaning properly removes all parenthetical content."""

    # Test basic subject cleaning
    subject, room = clean_subject("Matemātika")
    assert subject == "Matemātika"
    assert room is None

    # Test subject with room
    subject, room = clean_subject("Matemātika 210")
    assert subject == "Matemātika"
    assert room == "210"

    # Test subject with (I) suffix - should be removed
    subject, room = clean_subject("Tautas dejas kol. 'Balaguri' (I)")
    assert subject == "Tautas dejas kol. 'Balaguri'"
    assert room is None

    # Test subject with (F) suffix - should be removed
    subject, room = clean_subject("Matemātika F (F)")
    assert subject == "Matemātika F"
    assert room is None

    # Test subject with multiple parentheses - all should be removed
    subject, room = clean_subject("Sports (F) (G)")
    assert subject == "Sports"
    assert room is None

    # Test subject with room and parentheses - parentheses should be removed
    subject, room = clean_subject("Matemātika F (F) 210")
    assert subject == "Matemātika F"
    assert room == "210"

    # Test subject with special room code
    subject, room = clean_subject("Sports un veselība mz")
    assert subject == "Sports un veselība"
    assert room == "mz"

    # Test subject with special room code and parentheses - parentheses should be removed
    subject, room = clean_subject("Sports un veselība (F) mz")
    assert subject == "Sports un veselība"
    assert room == "mz"

    # Test subject with nested parentheses - all should be removed
    subject, room = clean_subject("Matemātika (grupa (A))")
    assert subject == "Matemātika"
    assert room is None

    # Test subject with parentheses in quotes - parentheses in quotes should be preserved
    subject, room = clean_subject("Tautas dejas kol. 'Balaguri' (I)")
    assert subject == "Tautas dejas kol. 'Balaguri'"
    assert room is None

    # Test subject with room code and parentheses
    subject, room = clean_subject("Dejas un ritmika (F) az")
    assert subject == "Dejas un ritmika"
    assert room == "az"
