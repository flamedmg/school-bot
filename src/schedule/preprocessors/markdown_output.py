"""
Markdown Output Preprocessor
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Union

from src.database.models import Schedule


class MarkdownOutputError(Exception):
    """Raised when there's an error writing Markdown output"""

    pass


def save_schedule_markdown(
    data: Union[Schedule, list[dict[str, Any]]], output_path: str | Path
) -> Union[Schedule, list[dict[str, Any]]]:
    """Save schedule data as formatted Markdown"""
    try:
        output_path = Path(output_path)

        with output_path.open("w", encoding="utf-8") as f:
            f.write("# Class Schedule\n\n")
            f.write(
                f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            )

            if isinstance(data, Schedule):
                days = data.days
            elif len(data) == 1 and isinstance(data[0], dict) and "days" in data[0]:
                days = data[0]["days"]
            else:
                days = data

            for day in days:
                if isinstance(day, dict):
                    date = day.get("date")
                    lessons = day.get("lessons", [])
                    announcements = day.get("announcements", [])
                else:  # SchoolDay object
                    date = day.date
                    lessons = day.lessons
                    announcements = day.announcements

                date_str = (
                    date.strftime("%A, %B %d, %Y")
                    if isinstance(date, datetime)
                    else str(date)
                )
                f.write(f"## {date_str}\n\n")

                if lessons:
                    f.write("### Lessons\n\n")
                    for lesson in lessons:
                        if isinstance(lesson, dict):
                            index = lesson.get("index", "")
                            subject = lesson.get("subject", "")
                            room = lesson.get("room", "")
                            topic = lesson.get("topic")
                            homework = lesson.get("homework")
                            mark = lesson.get("mark")
                        else:  # Lesson object
                            index = lesson.index
                            subject = lesson.subject
                            room = lesson.room
                            topic = lesson.topic
                            homework = lesson.homework
                            mark = lesson.mark

                        f.write(f"**Period {index}**\n")
                        f.write(f"- Subject: {subject}\n")
                        f.write(f"- Room: {room}\n")
                        if topic:
                            f.write(f"- Topic: {topic}\n")

                        if homework:
                            f.write("- Homework:\n")
                            if isinstance(homework, dict):
                                text = homework.get("text")
                                attachments = homework.get("attachments", [])
                                links = homework.get("links", [])
                            else:  # Homework object
                                text = homework.text
                                attachments = homework.attachments
                                links = homework.links

                            if text:
                                f.write(f"  - {text}\n")
                            for attachment in attachments:
                                if isinstance(attachment, dict):
                                    filename = attachment["filename"]
                                    url = attachment["url"]
                                else:  # Attachment object
                                    filename = attachment.filename
                                    url = attachment.url
                                f.write(f"  - 📎 [{filename}]({url})\n")
                            for link in links:
                                if isinstance(link, dict):
                                    url = link.get("destination_url") or link.get(
                                        "original_url"
                                    )
                                else:  # Link object
                                    url = link.destination_url or link.original_url

                                if not url:
                                    continue  # Skip links with no URL

                                # Ensure the URL starts with 'http://' or 'https://'
                                if not url.startswith(("http://", "https://")):
                                    url = "https://" + url.lstrip("/")

                                # Use the last part of the URL as the link text
                                # or 'Link' if empty
                                link_text = url.split("/")[-1] or "Link"
                                f.write(f"  - 🔗 [{link_text}]({url})\n")

                        if mark:
                            f.write(f"- Mark: {mark}\n")
                        f.write("\n")

                if announcements:
                    f.write("### Announcements\n\n")
                    for announcement in announcements:
                        if isinstance(announcement, dict):
                            ann_type = announcement.get("type")
                            behavior_type = announcement.get("behavior_type", "")
                            description = announcement.get("description", "")
                            rating = announcement.get("rating", "")
                            text = announcement.get("text", "")
                        else:  # Announcement object
                            ann_type = announcement.type
                            behavior_type = announcement.behavior_type
                            description = announcement.description
                            rating = announcement.rating
                            text = announcement.text

                        if ann_type == "behavior":
                            f.write(f"**{behavior_type}**\n")
                            f.write(f"- Description: {description}\n")
                            f.write(f"- Rating: {rating}\n")
                        else:
                            f.write(f"- {text}\n")
                        f.write("\n")

                f.write("---\n\n")

        return data

    except Exception as e:
        raise MarkdownOutputError(f"Failed to save Markdown output: {str(e)}") from e


def create_markdown_output_step(output_path: str | Path):
    """Create a pipeline step function with configured output path"""

    def markdown_output_step(
        data: Union[Schedule, list[dict[str, Any]]]
    ) -> Union[Schedule, list[dict[str, Any]]]:
        return save_schedule_markdown(data, output_path)

    return markdown_output_step
