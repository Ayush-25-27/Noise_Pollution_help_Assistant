"""
noise_fetch_tool.py

Fetches the most recent logged reading for a location. In a real
deployment this would query your own database of crowdsourced
submissions (phone app, simple web form, or a physical sound-level
meter logging over MQTT/HTTP). Here it reads from a local JSON file
so the agent pipeline is fully runnable without any backend of your own.

Falls back to a bundled default if the location has no logged reading
yet, so a first-time location never breaks the flow.
"""

import json
from pathlib import Path

READINGS_PATH = Path(__file__).resolve().parents[3] / "data" / "sample_noise_readings.json"


def fetch_reading(location: str) -> dict:
    """
    Args:
        location: free-text location, e.g. "Near Lotus Public School, Sector 12"

    Returns:
        {"location": str, "db": int, "time_of_day": "day"|"night", "duration": "brief"|"sustained", "source": str}
    """
    with open(READINGS_PATH, "r") as f:
        readings = json.load(f)

    match = readings.get(location) or readings.get("_default")
    return {
        "location": location,
        "db": match["db"],
        "time_of_day": match["time_of_day"],
        "duration": match["duration"],
        "source": "logged_reading" if location in readings else "sample_data (no reading logged yet)",
    }


if __name__ == "__main__":
    print(fetch_reading("Near Lotus Public School, Sector 12"))
    print(fetch_reading("Some Unlogged Street"))
