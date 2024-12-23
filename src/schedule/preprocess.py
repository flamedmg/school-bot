import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from .preprocessors.announcements import preprocess_announcements
from .preprocessors.attachments import extract_attachments
from .preprocessors.dates import preprocess_dates_and_merge
from .preprocessors.exceptions import PreprocessingError
from .preprocessors.homework import preprocess_homeworks
from .preprocessors.lessons import preprocess_lessons
from .preprocessors.markdown_output import create_markdown_output_step
from .preprocessors.marks import preprocess_marks
from .preprocessors.to_schedule import to_schedule
from .preprocessors.translation import preprocess_translations
from src.database.models import Schedule


@dataclass
class PipelineStep:
    name: str
    function: Callable


class PreprocessingPipeline:
    def __init__(self, nickname: str | None = None, base_url: str | None = None):
        self.steps: list[PipelineStep] = []
        self.nickname = nickname
        self.base_url = base_url

    def add_step(self, name: str, function: Callable) -> "PreprocessingPipeline":
        self.steps.append(PipelineStep(name=name, function=function))
        return self

    def execute(self, data: Any) -> Schedule:
        result = data
        total_steps = len(self.steps)
        logger.info(f"Starting preprocessing pipeline with {total_steps} steps")

        for i, step in enumerate(self.steps, 1):
            try:
                logger.info(f"Step {i}/{total_steps}: Executing {step.name}")
                # Pass base_url to attachment preprocessor
                if step.name == "attachments" and self.base_url:
                    result = step.function(result, self.base_url)
                # Pass nickname to to_schedule step
                elif step.name == "to_schedule":
                    if not self.nickname:
                        raise ValueError("Nickname is required for to_schedule step")
                    result = step.function(result, self.nickname)
                else:
                    result = step.function(result)

                # Log counts based on result type
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, list | dict):
                            count = len(value)
                            logger.info(f"  - Processed {count} {key}")
                elif isinstance(result, list):
                    logger.info(f"  - Processed {len(result)} items")

            except PreprocessingError as e:
                logger.error(f"Preprocessing failed in step {step.name}:")
                logger.error(f"Error: {e.message}")
                logger.error(f"Invalid data: {e.invalid_data}")
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in preprocessing step {step.name}: {str(e)}"
                )
                logger.debug(f"Data causing error in {step.name}: {result}")
                logger.error("Stack trace:", traceback.format_exc())
                raise

        logger.info("Preprocessing pipeline completed successfully")
        return result


def create_default_pipeline(
    markdown_output_path: str | Path | None = None,
    nickname: str | None = None,
    base_url: str | None = None,
) -> PreprocessingPipeline:
    """Create the default preprocessing pipeline with all steps

    Args:
        markdown_output_path: Optional path for markdown output
        nickname: Optional nickname to identify which student this schedule belongs to
        base_url: Optional base URL for converting relative URLs to absolute URLs
    """
    pipeline = PreprocessingPipeline(nickname=nickname, base_url=base_url)

    # Add all preprocessing steps
    pipeline = (
        pipeline.add_step("dates", preprocess_dates_and_merge)
        .add_step("translations", preprocess_translations)
        .add_step("marks", preprocess_marks)
        .add_step("lessons", preprocess_lessons)
        .add_step("homework", preprocess_homeworks)
        .add_step("announcements", preprocess_announcements)
        .add_step("attachments", extract_attachments)
        .add_step("to_schedule", to_schedule)  # Add the new step
    )

    # Optionally add markdown output step if path is provided
    if markdown_output_path:
        pipeline.add_step(
            "markdown_output", create_markdown_output_step(markdown_output_path)
        )

    return pipeline
