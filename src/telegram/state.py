"""User state management for the Telegram bot."""

from dataclasses import dataclass
from typing import Dict, Optional
from src.config import StudentConfig


@dataclass
class UserState:
    """User state for menu navigation."""

    menu_selection: Optional[str] = None
    selected_student: Optional[StudentConfig] = None


# Global state storage
_user_states: Dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    """Get or create user state.

    Args:
        user_id: The user's Telegram ID

    Returns:
        The user's state object
    """
    if user_id not in _user_states:
        _user_states[user_id] = UserState()
    return _user_states[user_id]


def clear_user_state(user_id: int) -> None:
    """Clear user state.

    Args:
        user_id: The user's Telegram ID
    """
    if user_id in _user_states:
        del _user_states[user_id]
