"""Student selection handling functionality for the Telegram bot."""

from telethon import Button
from telethon.events import CallbackQuery, NewMessage
from datetime import datetime, time, timedelta
from loguru import logger

from src.config import settings
from src.telegram.state import get_user_state, clear_user_state
from src.telegram.constants import MenuOption
from src.telegram.services.schedule_service import ScheduleService
from src.database import AsyncSessionLocal


async def display_student_selection(
    event: NewMessage.Event | CallbackQuery.Event,
) -> None:
    """Display student selection buttons."""
    buttons = [
        [
            Button.inline(
                f"{student.emoji} {student.nickname.capitalize()}",
                data=f"student_{student.nickname}",
            )
        ]
        for student in settings.students
    ]

    await event.respond("Please select a student:", buttons=buttons)


async def display_schedule_options(event: CallbackQuery.Event) -> None:
    """Display schedule period selection buttons."""
    now = datetime.now()
    current_time = now.time()
    noon = time(12, 0)

    # Check if it's after noon
    is_after_noon = current_time >= noon
    # Check if it's Friday
    is_friday = now.weekday() == 4

    day_button_text = "Today"
    day_button_data = "schedule_day"

    # If it's after noon on a weekday, show tomorrow
    if is_after_noon and not is_friday:
        day_button_text = "Tomorrow"
    # If it's Friday after noon, show Monday
    elif is_friday and is_after_noon:
        day_button_text = "Monday"

    buttons = [
        [
            Button.inline(day_button_text, data=day_button_data),
            Button.inline("Next Week", data="schedule_week"),
        ]
    ]
    await event.respond("Please select schedule period:", buttons=buttons)


async def generate_student_response(menu_selection: str, student) -> str:
    """Generate response text based on menu selection and student."""
    base_text = f"{student.nickname.capitalize()}\n\n"

    if menu_selection == MenuOption.HOMEWORK.name.lower():
        return base_text + "Homework assignments will be implemented soon!"
    elif menu_selection == MenuOption.GRADES.name.lower():
        return base_text + "Grades will be implemented soon!"
    elif menu_selection == MenuOption.SETTINGS.name.lower():
        return base_text + "Settings will be implemented soon!"

    return "Invalid menu selection"


async def handle_student_callback(
    event: CallbackQuery.Event, student_nickname: str
) -> None:
    """Handle student selection and show requested information."""
    user_id = event.sender_id
    state = get_user_state(user_id)

    if not state.menu_selection:
        await event.answer("Please select an option from the menu first")
        return

    # Find selected student
    selected_student = next(
        (s for s in settings.students if s.nickname == student_nickname), None
    )
    if not selected_student:
        await event.answer("Student not found")
        return

    # Edit the original message to remove buttons
    await event.edit(selected_student.nickname.capitalize())

    # Handle schedule selection differently
    if state.menu_selection == MenuOption.SCHEDULE.name.lower():
        state.selected_student = selected_student
        await display_schedule_options(event)
        return

    # Generate response based on menu selection
    response_text = await generate_student_response(
        state.menu_selection, selected_student
    )

    # Clear user state after handling
    clear_user_state(user_id)

    # Send the full response in a new message
    await event.respond(response_text)


async def handle_schedule_callback(event: CallbackQuery.Event, period: str) -> None:
    """Handle schedule period selection.

    Args:
        event: The callback query event
        period: Either 'day' or 'week'
    """
    try:
        user_id = event.sender_id
        state = get_user_state(user_id)

        if not state.selected_student:
            await event.answer("Please select a student first")
            return

        is_day_schedule = period == "day"
        is_next_week = period == "schedule_week"
        logger.info(
            f"Schedule request: day={is_day_schedule}, next_week={is_next_week}"
        )

        # Get schedule from database
        async with AsyncSessionLocal() as session:
            schedule_service = ScheduleService(session)
            current_date = datetime.now()

            # Adjust the date based on time and day of week
            if is_day_schedule:
                noon = time(12, 0)
                is_after_noon = current_date.time() >= noon
                is_friday = current_date.weekday() == 4

                if is_after_noon and not is_friday:
                    # If after noon on weekday, show tomorrow
                    current_date = current_date + timedelta(days=1)
                elif is_friday and is_after_noon:
                    # If after noon on Friday, show Monday
                    days_until_monday = 3
                    current_date = current_date + timedelta(days=days_until_monday)

            logger.info(
                f"Getting schedule for {state.selected_student.nickname} on {current_date}"
            )

            try:
                if is_day_schedule:
                    schedule_data = await schedule_service.get_day_schedule(
                        state.selected_student.nickname, current_date
                    )
                else:
                    schedule_data = await schedule_service.get_week_schedule(
                        state.selected_student.nickname, current_date, is_next_week
                    )

                if not schedule_data:
                    await event.respond(
                        f"No schedule available for {state.selected_student.nickname.capitalize()}"
                    )
                    return

                # Format the schedule
                if is_day_schedule:
                    message = ["<pre>"]
                    for lesson in schedule_data["lessons"]:
                        message.append(
                            f"{lesson['time']} – {lesson['subject']} | Room {lesson['room']}"
                        )
                    message.append("</pre>")
                    schedule_text = "\n".join(message)
                else:
                    message = []
                    for day, lessons in schedule_data.items():
                        if lessons:
                            message.append(f"{day}:")
                            message.append("<pre>")
                            for lesson in lessons:
                                message.append(
                                    f"{lesson['time']} – {lesson['subject']} | Room {lesson['room']}"
                                )
                            message.append("</pre>")
                        else:
                            message.append(f"{day}: No classes")
                        message.append("")  # Empty line between days
                    schedule_text = "\n".join(message)

                # Clear user state after handling
                clear_user_state(user_id)

                # Send the full response in a new message
                await event.respond(schedule_text, parse_mode="html")

            except Exception as e:
                logger.error(f"Error getting schedule: {str(e)}")
                await event.respond(
                    f"❌ Error getting schedule for {state.selected_student.nickname.capitalize()}"
                )

    except Exception as e:
        logger.error(f"Error in handle_schedule_callback: {str(e)}")
        await event.respond("❌ An error occurred. Please try again later.")
