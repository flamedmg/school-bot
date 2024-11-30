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

from loguru import logger

from .exceptions import MarkPreprocessingError


def convert_single_mark(mark: str | int | None, context: dict = None) -> int | None:
    """
    Convert a single mark to the standardized 1-10 scale.
    Returns None for non-string input.
    Raises MarkPreprocessingError if conversion of string input fails.
    """
    # Handle non-string input by returning None
    if not isinstance(mark, str):
        return None

    # Store original mark for error reporting
    original_mark = mark

    # Remove whitespace and convert to uppercase for processing
    mark = mark.strip().upper()

    # Handle NC case
    if mark == "NC":
        return None

    # Handle empty string
    if not mark:
        raise MarkPreprocessingError(
            "Unable to convert mark: empty string",
            {"mark": original_mark, "context": context},
        )

    # Handle percentage case
    if "%" in mark:
        try:
            # Replace comma with period before converting to float
            percentage = float(mark.replace("%", "").replace(",", "."))
            converted = int(percentage / 10 + 0.5)
            logger.debug(f"Converted percentage mark '{original_mark}' to {converted}")
            return converted
        except ValueError as e:
            raise MarkPreprocessingError(
                f"Unable to convert percentage mark '{original_mark}' to numeric value",
                {"mark": original_mark, "context": context},
            ) from e

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
    except ValueError as e:
        raise MarkPreprocessingError(
            f"Unable to convert mark '{original_mark}' to valid score",
            {"mark": original_mark, "context": context},
        ) from e


def calculate_average_mark(
    marks: list[str] | None | int | str | dict, context: dict = None
) -> int | None:
    """
    Convert multiple marks and calculate their average.
    Returns None for non-list input.
    Raises MarkPreprocessingError if conversion of any mark fails.
    """
    # Handle non-list input by returning None
    if not isinstance(marks, list):
        return None

    if not marks:
        return None

    converted_marks = []
    for mark in marks:
        converted = convert_single_mark(mark, context)
        if converted is not None:
            converted_marks.append(converted)

    if not converted_marks:
        return None

    average = sum(converted_marks) / len(converted_marks)
    rounded = round(average)
    logger.debug(
        f"Calculated average {average:.2f} rounded to {rounded} "
        f"from {len(converted_marks)} marks"
    )
    return rounded


def preprocess_marks(
    data: list[dict] | None | int | str,
) -> list[dict] | None | int | str:
    """
    Process marks in the schedule data, converting all marks to a 1-10 scale
    and calculating averages where multiple marks exist.
    Returns input unchanged if it's not a list or is invalid.
    """
    # Return input unchanged if it's not a list
    if not isinstance(data, list):
        return data

    total_days = 0
    total_lessons_with_marks = 0
    total_marks_processed = 0
    total_marks_converted = 0

    # Handle case where input is a list containing a single dictionary with 'days' key
    if len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
        if not isinstance(data[0]["days"], list):
            return data
        days = data[0]["days"]
        wrap_output = True
    else:
        days = data
        wrap_output = False

    # Return input unchanged if days contains non-dict elements
    if not all(isinstance(day, dict) for day in days):
        return data

    total_days = len(days)
    logger.info(f"Processing marks for {total_days} days")

    for day in days:
        lessons = day.get("lessons", [])

        # Skip if lessons is not a list
        if not isinstance(lessons, list):
            continue

        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue

            # Get marks from lesson
            marks = lesson.get("mark")
            if not marks:
                lesson.pop("mark", None)
                continue

            # Skip if marks is not a list
            if not isinstance(marks, list):
                lesson.pop("mark", None)
                continue

            total_lessons_with_marks += 1
            total_marks_processed += len(marks)

            context = {
                "subject": lesson.get("subject", "Unknown"),
                "date": day.get("date", "Unknown"),
            }

            try:
                scores = [
                    mark.get("score", "") for mark in marks if isinstance(mark, dict)
                ]
                average = calculate_average_mark(scores, context)
                if average is not None:
                    lesson["mark"] = average
                    total_marks_converted += len(marks)
                else:
                    lesson.pop("mark", None)
            except MarkPreprocessingError as e:
                raise MarkPreprocessingError(
                    "Failed to process marks for lesson "
                    f"{lesson.get('subject', 'Unknown')}",
                    {"lesson": lesson, "context": context, "original_error": e},
                ) from e

    logger.info("Successfully processed marks:")
    logger.info(f"  - {total_lessons_with_marks} lessons with marks")
    logger.info(f"  - {total_marks_processed} total marks processed")
    logger.info(f"  - {total_marks_converted} marks successfully converted")

    # Return in same format as input
    return [{"days": days}] if wrap_output else days
