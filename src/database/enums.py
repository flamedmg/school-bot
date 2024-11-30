from enum import Enum


class ChangeType(str, Enum):
    """Type of change detected in data"""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
