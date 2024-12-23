from datetime import datetime


class CrawlError(Exception):
    """Base exception for crawling errors"""

    def __init__(
        self,
        error_type: str,
        message: str,
        screenshot_path: str | None = None,
        student_nickname: str | None = None,
    ):
        self.error_type = error_type
        self.message = message
        self.screenshot_path = screenshot_path
        self.student_nickname = student_nickname
        self.timestamp = datetime.now()
        super().__init__(message)


class LoginError(CrawlError):
    """Raised when login fails"""

    def __init__(
        self,
        message: str,
        screenshot_path: str | None = None,
        student_nickname: str | None = None,
    ):
        super().__init__("login_error", message, screenshot_path, student_nickname)


class FetchError(CrawlError):
    """Raised when fetching schedule fails"""

    def __init__(
        self,
        message: str,
        screenshot_path: str | None = None,
        student_nickname: str | None = None,
    ):
        super().__init__("fetch_error", message, screenshot_path, student_nickname)


class ParseError(CrawlError):
    """Raised when parsing schedule fails"""

    def __init__(
        self,
        message: str,
        screenshot_path: str | None = None,
        student_nickname: str | None = None,
    ):
        super().__init__("parse_error", message, screenshot_path, student_nickname)


class ProcessError(CrawlError):
    """Raised when processing schedule fails"""

    def __init__(
        self,
        message: str,
        screenshot_path: str | None = None,
        student_nickname: str | None = None,
    ):
        super().__init__("process_error", message, screenshot_path, student_nickname)
