class PreprocessingError(Exception):
    """Base exception for preprocessing errors"""

    def __init__(self, message: str, data: any = None):
        self.message = message
        self.invalid_data = data
        super().__init__(self.message)


class MarkPreprocessingError(PreprocessingError):
    """Raised when mark preprocessing fails"""

    pass


class DatePreprocessingError(PreprocessingError):
    """Raised when date preprocessing fails"""

    pass
