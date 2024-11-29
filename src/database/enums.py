from enum import Enum
from src.schedule.schema import AnnouncementType

class ChangeType(str, Enum):
    """Type of change detected in data"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
