"""
classification_tool.py

Two deterministic (non-LLM) judgments, kept rule-based on purpose:

1. Legal-limit check: is this dB reading over the limit for this zone
   type and time of day? This is a fixed regulatory threshold lookup —
   never left to a model's judgment, because a tool whose whole point
   is to be usable as evidence can't have a fuzzy, unreproducible
   verdict at its core.

2. Source inference: a simple heuristic over duration + time-of-day +
   intensity. This is *not* a trained classifier — it's a transparent
   rule table, which means you can always explain exactly why the
   tool guessed "construction" vs "traffic". Swap this for a real
   trained audio classifier later if you get access to labeled data;
   the interface (`infer_source`) doesn't need to change.

Limits approximate India's Noise Pollution (Regulation and Control)
Rules zone categories. Adjust ZONE_LIMITS if your local jurisdiction differs.
"""

ZONE_LIMITS = {
    "residential": {"day": 55, "night": 45},
    "silence": {"day": 50, "night": 40},       # schools, hospitals, courts
    "commercial": {"day": 65, "night": 55},
    "industrial": {"day": 75, "night": 70},
}

ZONE_LABELS = {
    "residential": "a residential zone",
    "silence": "a silence zone (school/hospital)",
    "commercial": "a commercial zone",
    "industrial": "an industrial zone",
}


def check_limit(db: int, zone: str, time_of_day: str) -> dict:
    """
    Args:
        db: measured decibel reading
        zone: "residential" | "silence" | "commercial" | "industrial"
        time_of_day: "day" | "night"

    Returns:
        {"limit": int, "exceeds": bool, "over_by": int}
    """
    limit = ZONE_LIMITS[zone][time_of_day]
    return {
        "limit": limit,
        "exceeds": db > limit,
        "over_by": max(0, db - limit),
    }


def infer_source(db: int, time_of_day: str, duration: str) -> str:
    """
    Args:
        db: measured decibel reading
        time_of_day: "day" | "night"
        duration: "brief" | "sustained"

    Returns:
        a short, human-readable likely-source explanation
    """
    if duration == "brief" and db >= 85:
        return "a short, high-intensity event \u2014 likely a loudspeaker announcement, celebration, or vehicle horn burst"
    if duration == "sustained" and time_of_day == "night":
        return "a sustained nighttime source \u2014 likely a generator, late-running machinery, or an ongoing event"
    if duration == "sustained" and time_of_day == "day" and db >= 75:
        return "a sustained daytime high-intensity source \u2014 likely construction or industrial equipment"
    if duration == "sustained" and time_of_day == "day":
        return "a sustained moderate source \u2014 likely regular traffic flow"
    return "a source that doesn't clearly match a single common pattern \u2014 worth a second reading to confirm"


if __name__ == "__main__":
    print(check_limit(78, "residential", "night"))
    print(infer_source(78, "night", "sustained"))
