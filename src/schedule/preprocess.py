import json
import logging
from datetime import datetime
from pathlib import Path
from .preprocessors.attachments import extract_attachments
from .preprocessors.dates import preprocess_dates_and_merge
from .preprocessors.marks import preprocess_marks
from .preprocessors.lessons import preprocess_lessons
from .preprocessors.announcements import preprocess_announcements
from .preprocessors.homework import preprocess_homeworks
from .preprocessors.translation import preprocess_translations
from .preprocessors.markdown_output import create_markdown_output_step
from .preprocessors.exceptions import PreprocessingError
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    name: str
    function: Callable


class PreprocessingPipeline:
    def __init__(self):
        self.steps: List[PipelineStep] = []

    def add_step(self, name: str, function: Callable) -> "PreprocessingPipeline":
        self.steps.append(PipelineStep(name=name, function=function))
        return self

    def execute(self, data: Any) -> Any:
        result = data
        total_steps = len(self.steps)
        logger.info(f"Starting preprocessing pipeline with {total_steps} steps")

        for i, step in enumerate(self.steps, 1):
            try:
                logger.info(f"Step {i}/{total_steps}: Executing {step.name}")
                result = step.function(result)

                # Log counts based on result type
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, (list, dict)):
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
                raise

        logger.info("Preprocessing pipeline completed successfully")
        return result


def create_default_pipeline(markdown_output_path: Optional[Union[str, Path]] = None):
    """Create the default preprocessing pipeline with all steps"""
    pipeline = PreprocessingPipeline()

    # Add all preprocessing steps
    pipeline = (
        pipeline.add_step("dates", preprocess_dates_and_merge)
        .add_step("translations", preprocess_translations)
        .add_step("marks", preprocess_marks)
        .add_step("lessons", preprocess_lessons)
        .add_step("homework", preprocess_homeworks)
        .add_step("announcements", preprocess_announcements)
        .add_step("attachments", extract_attachments)
    )

    # Optionally add markdown output step if path is provided
    if markdown_output_path:
        pipeline.add_step(
            "markdown_output", create_markdown_output_step(markdown_output_path)
        )

    return pipeline
