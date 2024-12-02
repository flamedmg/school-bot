"""Telegram bot handlers package."""

from src.telegram.handlers.menu import handle_menu_callback
from src.telegram.handlers.student import handle_student_callback
from src.telegram.handlers.messages import (
    handle_hi_message,
    handle_menu_command,
    handle_start_command,
    send_welcome_message,
)

__all__ = [
    "handle_menu_callback",
    "handle_student_callback",
    "handle_hi_message",
    "handle_menu_command",
    "handle_start_command",
    "send_welcome_message",
]
