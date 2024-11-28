import json
from loguru import logger
from datetime import datetime

"""
Marks Preprocessor

This preprocessor handles conversion and normalization of different marking systems:

Input formats:
- Percentages (e.g. "85%") -> Converted to 1-10 scale by dividing by 10 and rounding
- Numbers (1-10) -> Used as-is
- Letters:
    - S (Satisfactory) -> 3
    - T (Transitional) -> 5  
    - A (Accomplished) -> 7
    - P (Proficient) -> 10
- NC (Not Completed) -> Removed from calculations
- Any other format -> Raises MarkPreprocessingError

For multiple marks, the preprocessor:
1. Converts each mark according to the rules above
2. Calculates the average of all valid marks
3. Rounds to the nearest integer
4. Assigns the result to the lesson

Example:
Input marks: ["85%", "A", "P", "NC"]
Processing:
1. 85% -> 9
2. A -> 7
3. P -> 10
4. NC -> skipped
Final result: round((9 + 7 + 10) / 3) = 9
"""

from typing import List, Union, Optional
import re
from .exceptions import MarkPreprocessingError


def convert_single_mark(mark: str, context: dict = None) -> Optional[int]:
    """
    Convert a single mark to the standardized 1-10 scale.
    Raises MarkPreprocessingError if conversion fails.
    """
    # Store original mark for error reporting
    original_mark = mark

    # Handle non-string input
    if not isinstance(mark, str):
        raise MarkPreprocessingError(
            f"Invalid mark type: {type(mark)}, expected string",
            {"mark": mark, "context": context},
        )

    # Remove any whitespace and convert to uppercase
    mark = mark.strip().upper()

    # Handle NC case
    if mark == "NC":
        return None

    # Handle percentage case
    if "%" in mark:
        try:
            # Replace comma with period before converting to float
            percentage = float(mark.replace("%", "").replace(",", "."))
            converted = int(percentage / 10 + 0.5)
            logger.debug(f"Converted percentage mark '{original_mark}' to {converted}")
            return converted
        except ValueError:
            raise MarkPreprocessingError(
                f"Unable to convert percentage mark '{original_mark}' to numeric value",
                {"mark": original_mark, "context": context},
            )

    # Handle letter grades
    letter_grades = {"S": 3, "T": 5, "A": 7, "P": 10}
    if mark in letter_grades:
        converted = letter_grades[mark]
        logger.debug(f"Converted letter mark '{original_mark}' to {converted}")
        return converted

    # Handle numeric case
    try:
        # Replace comma with period for numeric values too
        num = float(mark.replace(",", "."))
        if 1 <= num <= 10:
            converted = round(num)
            logger.debug(f"Converted numeric mark '{original_mark}' to {converted}")
            return converted
        raise MarkPreprocessingError(
            f"Numeric mark '{original_mark}' outside valid range 1-10",
            {"mark": original_mark, "context": context},
        )
    except ValueError:
        raise MarkPreprocessingError(
            f"Unable to convert mark '{original_mark}' to valid score",
            {"mark": original_mark, "context": context},
        )


def calculate_average_mark(marks: List[str], context: dict = None) -> Optional[int]:
    """
    Convert multiple marks and calculate their average.
    Raises MarkPreprocessingError if any conversion fails.
    """
    if not marks:
        return None

    if not isinstance(marks, list):
        raise MarkPreprocessingError(
            f"Invalid marks type: {type(marks)}, expected list",
            {"marks": marks, "context": context},
        )

    converted_marks = []
    for mark in marks:
        try:
            converted = convert_single_mark(mark, context)
            if converted is not None:
                converted_marks.append(converted)
        except MarkPreprocessingError as e:
            # Preserve the original error message
            raise MarkPreprocessingError(
                str(e),  # Use the original error message
                {
                    "marks": marks,
                    "failed_mark": mark,
                    "context": context,
                    "original_error": e,
                },
            ) from e

    if not converted_marks:
        return None

    average = sum(converted_marks) / len(converted_marks)
    rounded = round(average)
    logger.debug(
        f"Calculated average {average:.2f} rounded to {rounded} from {len(converted_marks)} marks"
    )
    return rounded


def preprocess_marks(data: List[dict]) -> List[dict]:
    """
    Process marks in the schedule data, converting all marks to a 1-10 scale
    and calculating averages where multiple marks exist.
    """
    # Input validation
    if not isinstance(data, list):
        raise MarkPreprocessingError(
            f"Invalid input type: {type(data)}, expected list", {"data": data}
        )

    total_days = 0
    total_lessons_with_marks = 0
    total_marks_processed = 0
    total_marks_converted = 0

    # Handle case where input is a list containing a single dictionary with 'days' key
    if len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
        if not isinstance(data[0]["days"], list):
            raise MarkPreprocessingError(
                "Invalid days type in input data", {"data": data}
            )
        days = data[0]["days"]
        wrap_output = True
    else:
        days = data
        wrap_output = False

    total_days = len(days)
    logger.info(f"Processing marks for {total_days} days")

    for day in days:
        if not isinstance(day, dict):
            raise MarkPreprocessingError(
                f"Invalid day type: {type(day)}, expected dict", {"day": day}
            )

        for lesson in day.get("lessons", []):
            if not isinstance(lesson, dict):
                raise MarkPreprocessingError(
                    f"Invalid lesson type: {type(lesson)}, expected dict",
                    {"lesson": lesson, "day": day},
                )

            # Skip if no marks field or if marks is empty/None
            marks = lesson.get("mark")
            if not marks:
                # Remove empty marks field
                lesson.pop("mark", None)
                continue

            if not isinstance(marks, list):
                raise MarkPreprocessingError(
                    f"Invalid marks type: {type(marks)}, expected list",
                    {"marks": marks, "lesson": lesson, "day": day},
                )

            total_lessons_with_marks += 1
            total_marks_processed += len(marks)

            context = {
                "subject": lesson.get("subject", "Unknown"),
                "date": day.get("date", "Unknown"),
            }

            scores = [mark.get("score", "") for mark in marks if isinstance(mark, dict)]
            try:
                average = calculate_average_mark(scores, context)
                if average is not None:
                    # Replace entire mark array with single integer
                    lesson["mark"] = average
                    total_marks_converted += len(marks)
                else:
                    # Remove mark field if no valid marks
                    lesson.pop("mark", None)
            except MarkPreprocessingError as e:
                raise MarkPreprocessingError(
                    f"Failed to process marks for lesson {lesson.get('subject', 'Unknown')}",
                    {"lesson": lesson, "context": context, "original_error": e},
                ) from e

    logger.info(f"Successfully processed marks:")
    logger.info(f"  - {total_lessons_with_marks} lessons with marks")
    logger.info(f"  - {total_marks_processed} total marks processed")
    logger.info(f"  - {total_marks_converted} marks successfully converted")

    # Return in same format as input
    return [{"days": days}] if wrap_output else days
