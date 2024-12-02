"""Base handler class for Telegram bot handlers."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Set

from loguru import logger
from telethon import events
from telethon.events import NewMessage, CallbackQuery


class BaseHandler(ABC):
    """Base class for all handlers."""

    def __init__(self):
        """Initialize the handler."""
        self.logger = logger

    @abstractmethod
    async def handle(self, event: Any) -> None:
        """Handle the event.

        Args:
            event: The event to handle
        """
        pass

    def log_event(self, event_type: str, details: Optional[Dict] = None) -> None:
        """Log an event with optional details.

        Args:
            event_type: Type of the event
            details: Optional dictionary with additional details
        """
        log_msg = f"Handling {event_type}"
        if details:
            log_msg += f": {details}"
        self.logger.info(log_msg)


class MessageHandler(BaseHandler):
    """Handler for text messages."""

    GREETING_PATTERNS: Set[str] = {"hi", "hey", "bot", "бот"}

    async def handle(self, event: NewMessage.Event) -> None:
        """Handle text messages.

        Args:
            event: The message event
        """
        if not event.message or not event.message.text:
            return

        text = event.message.text.strip().lower()
        self.log_event("message", {"text": text})

        if text in self.GREETING_PATTERNS:
            await self._handle_greeting(event)

    async def _handle_greeting(self, event: NewMessage.Event) -> None:
        """Handle greeting messages.

        Args:
            event: The message event
        """
        self.log_event("greeting")
        from src.telegram.handlers.menu import display_menu

        await display_menu(event)


class CommandHandler(BaseHandler):
    """Handler for command messages."""

    async def handle(self, event: NewMessage.Event) -> None:
        """Handle command messages.

        Args:
            event: The command event
        """
        if not event.message or not event.message.text:
            return

        command = event.message.text.strip().lower()
        self.log_event("command", {"command": command})

        handlers = {"/menu": self._handle_menu, "/start": self._handle_start}

        handler = handlers.get(command)
        if handler:
            await handler(event)

    async def _handle_menu(self, event: NewMessage.Event) -> None:
        """Handle /menu command.

        Args:
            event: The command event
        """
        from src.telegram.handlers.menu import display_menu

        await display_menu(event)

    async def _handle_start(self, event: NewMessage.Event) -> None:
        """Handle /start command.

        Args:
            event: The command event
        """
        from src.telegram.handlers.menu import display_menu

        await display_menu(event)


class CallbackHandler(BaseHandler):
    """Handler for callback queries."""

    async def handle(self, event: CallbackQuery.Event) -> None:
        """Handle callback queries.

        Args:
            event: The callback query event
        """
        try:
            data = event.data.decode("utf-8")
            self.log_event("callback", {"data": data})

            if data.startswith("menu_"):
                await self._handle_menu_callback(event, data[5:])
            elif data.startswith("student_"):
                from src.telegram.handlers.student import handle_student_callback

                await handle_student_callback(event, data[8:])
            elif data.startswith("schedule_"):
                from src.telegram.handlers.student import handle_schedule_callback

                await handle_schedule_callback(event, data[9:])

        except Exception as e:
            self.logger.error(f"Error handling callback: {str(e)}")
            raise

    async def _handle_menu_callback(
        self, event: CallbackQuery.Event, menu_type: str
    ) -> None:
        """Handle menu callbacks.

        Args:
            event: The callback query event
            menu_type: The menu option selected
        """
        from src.telegram.handlers.menu import handle_menu_callback

        await handle_menu_callback(event, menu_type)
