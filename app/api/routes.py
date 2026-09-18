from fastapi import APIRouter, HTTPException

from app.agent.orchestrator import get_report
from app.agent.llm_client import generate
from app.models.schemas import ChatRequest, ChatResponse, ReadingSubmission, ReportRequest, ReportResponse

router = APIRouter()


def _run_report(req: ReportRequest) -> ReportResponse:
    try:
        result = get_report(
            location=req.location,
            zone=req.zone,
            db=req.db,
            time_of_day=req.time_of_day,
            duration=req.duration,
            question=req.question,
        )
        return ReportResponse(**result)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid field value: {exc}") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="Data file missing on server.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@router.post("/report", response_model=ReportResponse)
def report(req: ReportRequest) -> ReportResponse:
    return _run_report(req)


@router.post("/chat", response_model=ReportResponse)
def chat(req: ReportRequest) -> ReportResponse:
    """Follow-up questions reuse the same orchestrator path as /report."""
    return _run_report(req)


# ── Xaya chatbot ──────────────────────────────────────────────────────────
_XAYA_SYSTEM = (
    "You are Xaya, a friendly and knowledgeable assistant for the Noise Pollution "
    "Awareness Map. You help residents of India understand noise pollution, their "
    "legal rights under the Noise Pollution (Regulation and Control) Rules 2000, "
    "and how to file complaints. Be concise (2–4 sentences), warm, and practical. "
    "When web search results are provided under [WEB SEARCH RESULTS], use the "
    "actual numbers, statistics, and facts from those results in your answer. "
    "Always cite the source URL when using a specific statistic. "
    "Never name specific individuals or businesses. If asked something unrelated to "
    "noise pollution, gently redirect to noise-related topics."
)


def _build_chat_prompt(message: str) -> str:
    """
    Augments the user message with live web search results so the LLM
    (or mock) can answer with real, up-to-date numbers.
    Falls back gracefully if the search times out or fails.
    """
    from app.agent.tools.web_search_tool import web_search

    # Search for any factual / stat query OR general noise-pollution questions
    stats_keywords = [
        "total", "how many", "number", "count", "cases", "complaints",
        "statistics", "data", "report", "filed", "recorded", "india",
        "percent", "%", "annual", "year", "2023", "2024",
        "what is", "tell me", "explain", "define", "about",
    ]
    msg_lower = message.lower()
    needs_search = any(kw in msg_lower for kw in stats_keywords)

    if not needs_search:
        return message

    # Build a focused search query by appending context if not already present
    query = message.strip()
    if "noise" not in msg_lower:
        query += " noise pollution"
    if "india" not in msg_lower:
        query += " India"

    snippets = web_search(query, max_results=5)
    if not snippets:
        return message  # no results — return original message unchanged

    # Format snippets block
    lines = ["[WEB SEARCH RESULTS]"]
    for i, s in enumerate(snippets, 1):
        src = f"  Source: {s['url']}" if s["url"] else ""
        lines.append(f"{i}. {s['title']}: {s['snippet']}{src}")
    lines.append("[END WEB SEARCH RESULTS]")
    lines.append("")
    lines.append(f"User question: {message}")

    return "\n".join(lines)


@router.post("/chat/message", response_model=ChatResponse)
def xaya_chat(req: ChatRequest) -> ChatResponse:
    """Free-text chat endpoint for the Xaya assistant widget."""
    try:
        enriched_prompt = _build_chat_prompt(req.message)
        reply = generate(_XAYA_SYSTEM, enriched_prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}") from exc
    return ChatResponse(reply=reply)


@router.post("/readings", status_code=201)
def submit_reading(body: ReadingSubmission) -> dict:
    """
    Submit a new noise reading for a location.
    Appends it to the local sample readings file (development only).
    In production, replace this with a database write.
    """
    import json
    from pathlib import Path

    readings_path = Path("data/sample_noise_readings.json")
    try:
        with open(readings_path, "r") as f:
            readings = json.load(f)
    except FileNotFoundError:
        readings = {}

    readings[body.location] = {
        "db": body.db,
        "time_of_day": body.time_of_day,
        "duration": body.duration,
    }

    with open(readings_path, "w") as f:
        json.dump(readings, f, indent=2)

    return {
        "status": "created",
        "location": body.location,
        "db": body.db,
        "time_of_day": body.time_of_day,
        "duration": body.duration,
    }
