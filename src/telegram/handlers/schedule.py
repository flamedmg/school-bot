"""Schedule handling functionality for the Telegram bot."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import html
from tabulate import tabulate


def get_next_weekday(current_date: datetime) -> datetime:
    """Get the next weekday (Monday-Friday) from the given date.

    Args:
        current_date: The current date

    Returns:
        The next weekday date
    """
    next_day = current_date + timedelta(days=1)
    while next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        next_day += timedelta(days=1)
    return next_day


def get_schedule_date(is_day_schedule: bool = True) -> Tuple[datetime, bool]:
    """Get the appropriate date for schedule based on current time.

    Args:
        is_day_schedule: True if requesting daily schedule, False for weekly

    Returns:
        Tuple of (target_date, is_next_period)
        - target_date: The date to show schedule for
        - is_next_period: True if showing next day/week
    """
    now = datetime.now()
    is_next_period = False

    if is_day_schedule:
        # For daily schedule
        if now.weekday() >= 5:  # Weekend
            target_date = get_next_weekday(now)
            is_next_period = True
        elif now.hour >= 12:  # After noon
            target_date = get_next_weekday(now)
            is_next_period = True
        else:
            target_date = now
    else:
        # For weekly schedule
        if now.weekday() >= 5 or (now.weekday() == 4 and now.hour >= 12):
            # Weekend or Friday after noon
            target_date = get_next_weekday(now + timedelta(days=7))
            is_next_period = True
        else:
            target_date = now

    return target_date, is_next_period


def get_weekday_name(date: datetime) -> str:
    """Get the name of the weekday.

    Args:
        date: The date to get weekday name for

    Returns:
        Weekday name (e.g., "Monday")
    """
    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return weekdays[date.weekday()]


def format_schedule(
    schedule_data: dict, is_day_schedule: bool = True, target_date: datetime = None
) -> str:
    """Format schedule data for Telegram output.

    Args:
        schedule_data: The schedule data to format
        is_day_schedule: True if formatting daily schedule, False for weekly
        target_date: The date for which the schedule is being shown

    Returns:
        Formatted schedule string
    """
    try:
        if not schedule_data:
            return "❌ No schedule available"

        if is_day_schedule:
            return format_daily_schedule(schedule_data, target_date)
        return format_weekly_schedule(schedule_data, target_date)
    except Exception as e:
        return f"❌ Error: {html.escape(str(e))}"


def format_daily_schedule(schedule_data: dict, target_date: datetime) -> str:
    """Format daily schedule for Telegram output.

    Args:
        schedule_data: The daily schedule data
        target_date: The date for which the schedule is being shown

    Returns:
        Formatted schedule string
    """
    date_str = target_date.strftime("%d.%m.%Y")
    weekday = get_weekday_name(target_date)

    # Header outside of pre tag
    message = [f"📅 {weekday}, {date_str}\n"]

    # Create table data
    headers = ["Time", "Subject", "Room"]
    table_data = []

    for lesson in schedule_data.get("lessons", []):
        table_data.append(
            [
                lesson.get("time", ""),
                html.escape(lesson.get("subject", "")),
                html.escape(lesson.get("room", "")),
            ]
        )

    if not table_data:
        return "\n".join(message + ["❌ No classes"])

    # Format table with tabulate
    table = tabulate(table_data, headers=headers, tablefmt="simple")
    return "\n".join(message + ["<pre>", table, "</pre>"])


def format_weekly_schedule(schedule_data: dict, start_date: datetime) -> str:
    """Format weekly schedule for Telegram output.

    Args:
        schedule_data: The weekly schedule data
        start_date: The start date of the week

    Returns:
        Formatted schedule string
    """
    formatted_days = []
    current_date = start_date
    headers = ["Time", "Subject", "Room"]

    for day, lessons in schedule_data.items():
        date_str = current_date.strftime("%d.%m.%Y")
        weekday = get_weekday_name(current_date)

        # Header outside of pre tag
        message = [f"📅 {weekday}, {date_str}\n"]

        if not lessons:
            message.append("❌ No classes")
            formatted_days.append("\n".join(message))
            current_date += timedelta(days=1)
            continue

        # Create table data
        table_data = []
        for lesson in lessons:
            table_data.append(
                [
                    lesson.get("time", ""),
                    html.escape(lesson.get("subject", "")),
                    html.escape(lesson.get("room", "")),
                ]
            )

        # Format table with tabulate
        table = tabulate(table_data, headers=headers, tablefmt="simple")
        formatted_days.append("\n".join(message + ["<pre>", table, "</pre>"]))
        current_date += timedelta(days=1)

    return "\n\n".join(formatted_days)
