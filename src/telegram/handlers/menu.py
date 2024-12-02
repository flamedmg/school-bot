"""Menu handling functionality for the Telegram bot."""

from loguru import logger
from telethon import Button
from telethon.events import CallbackQuery, NewMessage

from src.telegram.constants import MenuOption
from src.telegram.state import UserState, get_user_state, clear_user_state
from src.telegram.handlers.student import display_student_selection


async def log_user_selection(user_id: int, selection: str) -> None:
    """Log user menu selections."""
    logger.info(f"User {user_id} selected: {selection}")


async def display_menu(event: NewMessage.Event) -> None:
    """Display the main menu with inline buttons."""
    buttons = [
        [Button.inline(option.value, data=f"menu_{option.name.lower()}")]
        for option in MenuOption
    ]

    await event.respond("Please select an option:", buttons=buttons)


async def handle_menu_callback(event: CallbackQuery.Event, menu_type: str) -> None:
    """Handle menu option selection."""
    user_id = event.sender_id
    await log_user_selection(user_id, menu_type)

    # Store menu selection in user state
    state = get_user_state(user_id)
    state.menu_selection = menu_type

    # Edit the original message to remove buttons
    await event.edit(MenuOption[menu_type.upper()].value)

    # Show student selection in a new message
    await display_student_selection(event)
