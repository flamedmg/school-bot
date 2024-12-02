"""Constants and enums for the Telegram bot."""

from enum import Enum


class MenuOption(Enum):
    """Available menu options."""

    SCHEDULE = "📅 View Schedule"
    HOMEWORK = "📚 Check Homework"
    GRADES = "📊 View Grades"
    SETTINGS = "⚙️ Settings"


class CallbackPrefix:
    """Callback data prefixes."""

    MENU = "menu_"
    STUDENT = "student_"


class MessagePattern:
    """Message patterns for command handlers."""

    HI = r"(?i)^hi$"  # (?i) makes it case insensitive within the regex
    MENU = "/menu"
    START = "/start"
