"""
orchestrator.py

Same agentic shape as the AQI project: decide what's needed, run the
deterministic tools, retrieve grounding text, then generate.

Decision logic:
  1. Do we already have a reading, or do we need the noise fetch tool
     for this location?
  2. Always run the legal-limit check and source inference \u2014
     deterministic, never delegated to the LLM.
  3. Retrieve regulation passages relevant to the zone type and the
     free-text question (if any).
  4. Assemble the report prompt and call the LLM.
"""

from pathlib import Path

from app.agent.llm_client import generate
from app.agent.tools.classification_tool import ZONE_LABELS, check_limit, infer_source
from app.agent.tools.noise_fetch_tool import fetch_reading
from app.agent.tools.rag_retrieval_tool import retrieve_regulations

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_PROMPT = (PROMPTS_DIR / "system_prompt.md").read_text()
REPORT_TEMPLATE = (PROMPTS_DIR / "report_prompt.md").read_text()


def get_report(
    location: str,
    zone: str,
    db: int | None = None,
    time_of_day: str | None = None,
    duration: str | None = None,
    question: str | None = None,
) -> dict:
    """
    Full agent run for one user turn.

    Args:
        location: free-text location
        zone: "residential" | "silence" | "commercial" | "industrial"
        db, time_of_day, duration: optional \u2014 if omitted, the fetch tool supplies them
        question: optional free-text follow-up

    Returns:
        dict with the reading, classification, retrieved passages, and generated answer
    """
    # Step 1: fetch a reading only if the caller didn't already supply one.
    if db is None or time_of_day is None or duration is None:
        fetched = fetch_reading(location)
        db = db if db is not None else fetched["db"]
        time_of_day = time_of_day or fetched["time_of_day"]
        duration = duration or fetched["duration"]
        data_source = fetched["source"]
    else:
        data_source = "user_provided"

    # Step 2: deterministic classification \u2014 always runs.
    limit_check = check_limit(db, zone, time_of_day)
    source_guess = infer_source(db, time_of_day, duration)

    # Step 3: retrieval, scoped to zone type.
    retrieval_query = question or "is this reading enough to raise a complaint"
    passages = retrieve_regulations(query=retrieval_query, zone=zone, top_k=2)
    passages_block = "\n".join(f"- {p}" for p in passages) if passages else "- (no specific passage retrieved)"

    # Step 4: assemble the prompt and generate.
    exceeds_str = "YES — exceeds limit" if limit_check["exceeds"] else "NO — within limit"
    user_prompt = REPORT_TEMPLATE.format(
        location=location,
        db=db,
        time_of_day=time_of_day,
        duration=duration,
        zone=zone,
        limit=limit_check["limit"],
        exceeds=exceeds_str,
        over_by=limit_check["over_by"],
        source_guess=source_guess,
        regulation_passages=passages_block,
        question=question or "What should I take away from this reading?",
    )
    answer = generate(SYSTEM_PROMPT, user_prompt)

    return {
        "location": location,
        "zone": zone,
        "zone_label": ZONE_LABELS[zone],
        "db": db,
        "time_of_day": time_of_day,
        "duration": duration,
        "data_source": data_source,
        "limit": limit_check["limit"],
        "exceeds": limit_check["exceeds"],
        "over_by": limit_check["over_by"],
        "source_guess": source_guess,
        "regulation_passages": passages,
        "answer": answer,
    }


if __name__ == "__main__":
    result = get_report(
        location="Near Lotus Public School, Sector 12",
        zone="silence",
        db=78,
        time_of_day="night",
        duration="sustained",
        question="What can I actually do with this?",
    )
    for k, v in result.items():
        print(f"{k}: {v}\n")
