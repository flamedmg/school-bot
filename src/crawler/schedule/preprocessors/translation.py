from pathlib import Path
import yaml
from typing import Dict, List, Any
from .exceptions import PreprocessingError
from . import lessons  # Import the lessons module

class Translator:
    def __init__(self):
        self.translations = self._load_translations()
    
    def _load_translations(self) -> dict:
        try:
            translations_file = Path(__file__).parent.parent / "translations.yaml"
            with open(translations_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise PreprocessingError(f"Failed to load translations: {str(e)}")
    
    def translate_subject(self, text: str) -> str:
        if not text:
            return text
        return self.translations['subjects'].get(text, text)

def preprocess_translations(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Translate subject names in the schedule data.
    Should be run before lesson preprocessing.
    """
    try:
        translator = Translator()
        
        # Handle case where input is a list containing a single dictionary with 'days' key
        if len(data) == 1 and isinstance(data[0], dict) and 'days' in data[0]:
            days = data[0]['days']
            wrap_output = True
        else:
            days = data
            wrap_output = False

        for day in days:
            if not isinstance(day, dict):
                continue
                
            for lesson in day.get("lessons", []):
                if not isinstance(lesson, dict):
                    continue
                        
                if "subject" in lesson:
                    subject = lesson["subject"]
                    if subject:
                        # Extract subject name using clean_subject function
                        subject_name, _ = lessons.clean_subject(subject)
                        if subject_name:
                            # Translate the subject name
                            translated_name = translator.translate_subject(subject_name)
                            # Replace the subject with the translated name
                            lesson["subject"] = translated_name

        # Return in same format as input
        return [{"days": days}] if wrap_output else days
        
    except Exception as e:
        raise PreprocessingError(
            f"Failed to translate schedule data: {str(e)}",
            {"data": data}
        )
