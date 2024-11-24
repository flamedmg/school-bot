from pathlib import Path

def load_test_file(filename: str, *, base_dir: str | None = None) -> str:
    """
    Load content from a test file.
    
    Args:
        filename: Name of the file to load
        base_dir: Optional base directory path relative to tests folder. 
                 Example: "crawl/test_data"
    
    Returns:
        str: Content of the file
    """
    tests_dir = Path(__file__).parent
    if base_dir:
        file_path = tests_dir / base_dir / filename
    else:
        file_path = tests_dir / filename
        
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read() 