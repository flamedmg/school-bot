"""Tests for the Attachment model"""

import pytest
from pathlib import Path
from src.database.models import Attachment

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing"""
    # Create a temporary attachments directory
    attachments_dir = tmp_path / "data" / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    return attachments_dir

def test_get_file_path(temp_dir, monkeypatch):
    """Test the get_file_path method of Attachment model"""
    # Mock Path to redirect to temp directory
    original_path = Path
    
    class MockPath(type(Path())):
        def __new__(cls, *args):
            if len(args) == 1 and args[0] == "data/attachments":
                return original_path(temp_dir)
            return original_path(*args)
            
    monkeypatch.setattr("pathlib.Path", MockPath)
    
    attachment = Attachment(
        unique_id="202401_20240101_math_1",
        filename="test.pdf",
        url="/files/test.pdf",
        homework_id=1
    )

    path = attachment.get_file_path()

    assert isinstance(path, Path)
    assert "202401" in str(path.parent)
    assert path.name == f"{attachment.unique_id}_{attachment.filename}"

def test_get_file_path_creates_directory(temp_dir, monkeypatch):
    """Test that get_file_path creates the necessary directory structure"""
    # Mock Path to redirect to temp directory
    original_path = Path
    
    class MockPath(type(Path())):
        def __new__(cls, *args):
            if len(args) == 1 and args[0] == "data/attachments":
                return original_path(temp_dir)
            return original_path(*args)
            
    monkeypatch.setattr("pathlib.Path", MockPath)
    
    attachment = Attachment(
        unique_id="202401_20240101_math_1",
        filename="test.pdf",
        url="/test/url",
        homework_id=1
    )
    
    file_path = attachment.get_file_path()
    
    # Check that directory was created
    assert file_path.parent.exists()
    assert file_path.parent.is_dir()
    
    # Check correct path structure
    assert "202401" in str(file_path.parent)
    assert file_path.name == f"{attachment.unique_id}_{attachment.filename}"
