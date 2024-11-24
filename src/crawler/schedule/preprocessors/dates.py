import json
from datetime import datetime
from typing import List, Dict

def preprocess_dates_and_merge(data: list) -> list:
    """
    Preprocesses dates in the schedule data by:
    1. Extracting proper date from the first element
    2. Removing empty first element
    3. Fixing date format in the second element

    Args:
        data: List of schedule data dictionaries or list of days

    Returns:
        List with processed schedule data
    """

    if not data or not isinstance(data, list):
        print("Warning: Invalid input to dates preprocessor")
        return data

    # Early return for empty or malformed input
    if len(data) == 1:
        entry = data[0]
        if not entry or not isinstance(entry, dict):
            return data
        if "days" in entry and not isinstance(entry["days"], list):
            return data
        if not any(key in entry for key in ["days", "date"]):
            return data

    # Handle case where input is direct list of days
    if all(isinstance(d, dict) and "date" in d for d in data):
        days = data
    else:
        # Handle case where input is list of entries containing days
        days = []
        for entry in data:
            if not isinstance(entry, dict):
                print(f"Warning: Invalid entry type: {type(entry)}")
                continue
            if "days" not in entry or not isinstance(entry["days"], list):
                days.append(entry)
                continue
            days.extend(entry["days"])

    processed_days = []
    i = 0
    while i < len(days):
        if not isinstance(days[i], dict):
            print(f"Warning: Invalid day type at index {i}: {type(days[i])}")
            i += 1
            continue

        # Check if we have a date-only entry followed by content
        if (i + 1 < len(days) and
            isinstance(days[i+1], dict) and
            not days[i].get("lessons") and
            not days[i].get("announcements") and
            days[i].get("date") and
            days[i+1].get("date")):

            print(f"Found date-only entry followed by content at index {i}")

            try:
                # Extract date from first element
                date_str = days[i]["date"]  # Format: "11.11.24. pirmdiena"
                print(f"Extracting date from: {date_str}")

                # Remove day name and extra dots
                clean_date = date_str.split()[0].rstrip('.')
                print(f"Cleaned date string: {clean_date}")
                date_obj = datetime.strptime(clean_date, "%d.%m.%y")
                print(f"Parsed date object: {date_obj}")

                # Create new day entry with proper date
                day_entry = days[i+1].copy()
                day_entry["date"] = date_obj
                processed_days.append(day_entry)

                # Skip both entries
                i += 2
                continue

            except (ValueError, IndexError) as e:
                print(f"Warning: Failed to process date at index {i}: {e}")
                processed_days.append(days[i])
                i += 1
                continue

        # Handle single entry
        processed_days.append(days[i])
        i += 1

    # Return in the same format as input
    if all(isinstance(d, dict) and "date" in d for d in data):
        return processed_days
    else:
        return data if not processed_days else [{"days": processed_days}]
