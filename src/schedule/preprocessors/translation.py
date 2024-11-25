from pathlib import Path
import yaml
from loguru import logger
from typing import Dict, List, Any
from .exceptions import PreprocessingError
from . import lessons  # Import the lessons module


class Translator:
    def __init__(self):
        self.translations = self._load_translations()

    def _load_translations(self) -> dict:
        try:
            translations_file = Path(__file__).parent.parent / "translations.yaml"
            with open(translations_file, "r", encoding="utf-8") as f:
                translations = yaml.safe_load(f)
                logger.debug(
                    f"Loaded {len(translations.get('subjects', {}))} subject translations"
                )
                return translations
        except Exception as e:
            raise PreprocessingError(f"Failed to load translations: {str(e)}")

    def translate_subject(self, text: str) -> str:
        if not text:
            return text
        translated = self.translations["subjects"].get(text, text)
        if translated != text:
            logger.debug(f"Translated subject '{text}' to '{translated}'")
        return translated


def preprocess_translations(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Translate subject names in the schedule data.
    Should be run before lesson preprocessing.
    """
    try:
        translator = Translator()
        total_days = 0
        total_lessons = 0
        total_subjects = 0
        translated_subjects = 0

        # Handle case where input is a list containing a single dictionary with 'days' key
        if len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
            days = data[0]["days"]
            wrap_output = True
        else:
            days = data
            wrap_output = False

        total_days = len(days)
        logger.info(f"Processing translations for {total_days} days")

        for day in days:
            if not isinstance(day, dict):
                continue

            day_lessons = day.get("lessons", [])
            total_lessons += len(day_lessons)

            for lesson in day_lessons:
                if not isinstance(lesson, dict):
                    continue

                if "subject" in lesson:
                    subject = lesson["subject"]
                    if subject:
                        total_subjects += 1
                        # Extract subject name using clean_subject function from the lessons module
                        subject_name, _ = lessons.clean_subject(subject)
                        if subject_name:
                            # Translate the subject name
                            translated_name = translator.translate_subject(subject_name)
                            if translated_name != subject_name:
                                translated_subjects += 1
                            # Replace the subject with the translated name
                            lesson["subject"] = translated_name

        logger.info(f"Successfully processed translations:")
        logger.info(f"  - {total_lessons} lessons checked")
        logger.info(f"  - {total_subjects} subjects found")
        logger.info(f"  - {translated_subjects} subjects translated")

        # Return in same format as input
        return [{"days": days}] if wrap_output else days

    except Exception as e:
        raise PreprocessingError(
            f"Failed to translate schedule data: {str(e)}", {"data": data}
        )
