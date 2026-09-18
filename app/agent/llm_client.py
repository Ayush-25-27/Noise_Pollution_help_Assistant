"""
llm_client.py

One generate() function, provider chosen by the LLM_PROVIDER env var.
- mock: runs fully offline, no key needed (default)
- anthropic: uses Claude via the anthropic SDK
- watsonx: uses IBM Granite via ibm-watsonx-ai SDK (IAM token handled by SDK)
"""

import os


def generate(system_prompt: str, user_prompt: str) -> str:
    provider = os.environ.get("LLM_PROVIDER", "mock")
    if provider == "anthropic":
        return _generate_anthropic(system_prompt, user_prompt)
    if provider == "watsonx":
        return _generate_watsonx(system_prompt, user_prompt)
    if provider == "openrouter":
        return _generate_openrouter(system_prompt, user_prompt)
    return _generate_mock(system_prompt, user_prompt)


def _generate_mock(system_prompt: str, user_prompt: str) -> str:
    """
    A rule-based mock that extracts key fields from the formatted prompt and
    returns a contextual plain-language advisory so the UI is useful even
    without a real LLM key.

    When called from the Xaya chat endpoint the user_prompt is raw freetext
    rather than a structured report template.  We detect this by checking for
    the "Location:" field marker and branch into a simple keyword reply tree.
    """
    import re

    def _field(label: str) -> str:
        m = re.search(rf"{label}:\s*(.+)", user_prompt)
        return m.group(1).strip() if m else ""

    # ── Detect raw chat message (no structured fields) ─────────────────────
    is_chat = not bool(re.search(r"Location:\s*.+", user_prompt))
    if is_chat:

        # ── If web search results were injected, use them directly ──────────
        web_block = re.search(
            r"\[WEB SEARCH RESULTS\](.*?)\[END WEB SEARCH RESULTS\]",
            user_prompt, re.DOTALL
        )
        if web_block:
            raw_snippets = web_block.group(1).strip()
            # Extract the original user question (last line after the block)
            user_q_match = re.search(r"User question:\s*(.+)", user_prompt)
            user_q = user_q_match.group(1).strip() if user_q_match else ""

            # Pull out numbered lines: "1. Title: snippet  Source: url"
            entries = re.findall(r"\d+\.\s+([^\n]+)", raw_snippets)
            if entries:
                summary_lines = []
                for e in entries[:4]:
                    # Split off "  Source: <url>" suffix
                    parts = re.split(r"\s{2,}Source:\s*", e, maxsplit=1)
                    text = parts[0].strip()
                    src  = parts[1].strip() if len(parts) > 1 else ""
                    # Strip "Title: " prefix — only if the title portion is
                    # a short word (≤60 chars) before the first ": "
                    text = re.sub(r"^.{1,60}?:\s+", "", text, count=1)
                    if text:
                        line = f"• {text}"
                        if src:
                            # shorten long URLs
                            domain = re.sub(r"https?://(www\.)?", "", src).split("/")[0]
                            line += f" — {domain}"
                        summary_lines.append(line)

                note = "\n\n[Live web results via DuckDuckGo — set LLM_PROVIDER=anthropic or watsonx for AI-synthesised answers]"
                if summary_lines:
                    intro = f'Here\'s what I found on the web for "{user_q}":\n\n' if user_q else "Here's what I found:\n\n"
                    return intro + "\n".join(summary_lines) + note
            # If parsing failed, fall through to keyword tree with original msg
            msg = (user_q or user_prompt).lower()
        else:
            msg = user_prompt.lower()

        if any(w in msg for w in ["silence zone", "silence"]):
            reply = (
                "A Silence Zone is a 100-metre radius around hospitals, educational "
                "institutions, courts, and religious places. The legal noise limit is "
                "50 dB during the day and 40 dB at night. Honking inside a silence "
                "zone is a cognizable offence under India's Noise Pollution Rules 2000."
            )
        elif any(w in msg for w in ["limit", "legal", "law", "rule", "allowed", "maximum"]):
            reply = (
                "India's Noise Pollution (Regulation and Control) Rules 2000 set these "
                "daytime / nighttime limits: Silence zone 50/40 dB, Residential 55/45 dB, "
                "Commercial 65/55 dB, Industrial 75/70 dB. Exceeding these limits is "
                "actionable under Section 268 IPC and the Environment Protection Act 1986."
            )
        elif any(w in msg for w in ["complaint", "complain", "report", "file", "raise", "rwa"]):
            reply = (
                "To file a noise complaint: (1) log 3–5 timestamped dB readings, "
                "(2) submit a written complaint to your local Pollution Control Board "
                "or use the CPCB online grievance portal, (3) CC your ward office and "
                "Resident Welfare Association (RWA). Under Rule 7 you don't need a lawyer."
            )
        elif any(w in msg for w in ["health", "harm", "effect", "damage", "hearing", "safe", "risk"]):
            reply = (
                "Prolonged exposure above 70 dB causes hearing fatigue; above 85 dB risks "
                "permanent damage. WHO guidelines recommend nighttime outdoor levels below "
                "40 dB for healthy sleep. Chronic noise exposure also raises stress hormones "
                "and blood pressure, increasing cardiovascular risk."
            )
        elif any(w in msg for w in ["source", "cause", "coming from", "who is"]):
            reply = (
                "Common noise sources in Indian cities include: construction activity "
                "(daytime), loudspeakers and DJ systems (events), industrial machinery, "
                "traffic and horn use, and generators. The time pattern of the noise "
                "usually points to the source — machinery tends to be continuous, while "
                "traffic noise peaks at rush hours."
            )
        elif any(w in msg for w in ["hi", "hello", "hey", "help", "what can"]):
            reply = (
                "Hi! I'm Xaya, your noise pollution guide. I can help you understand "
                "India's noise limits, how to file complaints, identify noise sources, "
                "and learn about the health effects of noise. What would you like to know?"
            )
        else:
            reply = (
                "I'm here to help with noise pollution questions — legal limits, filing "
                "complaints, identifying sources, or health effects. Could you tell me "
                "more about what you'd like to know?"
            )
        note = "\n\n[Mock response — set LLM_PROVIDER=anthropic or watsonx for AI-generated answers]"
        return reply + note

    location   = _field("Location")
    reading    = _field("Reading")
    zone       = _field("Zone type")
    exceeds    = _field("Exceeds limit")
    source     = _field("Likely source")
    question   = _field("Question")

    over_match = re.search(r"over by (\d+) dB", exceeds)
    over_by    = int(over_match.group(1)) if over_match else 0

    is_exceeded = exceeds.upper().startswith("YES")

    # Build a direct answer to the user's question
    q_lower = question.lower()

    if any(w in q_lower for w in ["complaint", "complain", "report", "file", "raise"]):
        action = (
            "To file a complaint: (1) log at least 3–5 readings with timestamps to build "
            "a pattern, (2) submit a written complaint with this evidence to your local "
            "Pollution Control Board or use the CPCB's online grievance portal, "
            "(3) CC your ward office and Resident Welfare Association (RWA). "
            "Under Rule 7 of India's Noise Pollution Rules 2000, any person may lodge "
            "a complaint to the authority — you don't need a lawyer."
        )
    elif any(w in q_lower for w in ["source", "cause", "coming from", "who"]):
        action = (
            f"Based on the reading profile ({reading}), the likely source is {source}. "
            "To confirm: note the time pattern — does the noise peak at specific hours? "
            "A recurring nighttime pattern often points to machinery or a generator, "
            "while short daytime bursts suggest construction or vehicles."
        )
    elif any(w in q_lower for w in ["limit", "legal", "law", "rule", "regulation", "allowed"]):
        action = (
            f"In a {zone}, the measurement of {reading} is checked against the legal "
            f"limit. {exceeds}. India's Noise Pollution (Regulation and Control) Rules 2000 "
            "set these limits; silence zones carry the strictest thresholds (50 dB day / "
            "40 dB night), with horn use near them being a cognizable offence."
        )
    elif any(w in q_lower for w in ["evidence", "proof", "document", "record", "log"]):
        action = (
            "Good evidence for a noise complaint: timestamped dB readings (a free app like "
            "NIOSH SLM is acceptable), a brief written log noting duration and any visible "
            "source, and photos/video if safe to take. Repeated logs across multiple days "
            "carry far more weight than a single reading."
        )
    elif any(w in q_lower for w in ["safe", "health", "harm", "danger", "risk", "effect"]):
        action = (
            f"At {reading}, prolonged exposure above 70 dB can cause hearing fatigue; "
            "above 85 dB risks permanent damage. WHO guidelines recommend nighttime "
            "outdoor levels below 40 dB for sleep. Repeated exposure at these levels "
            "warrants both personal protection (earplugs when near the source) and "
            "a formal complaint to limit community-wide impact."
        )
    else:
        # Generic contextual fallback
        if is_exceeded:
            action = (
                f"This reading exceeds the legal limit by {over_by} dB. "
                "Document it with a timestamp, note the likely source, and if the pattern "
                "repeats, compile 3–5 logs before filing a complaint with your local "
                "Pollution Control Board or ward office under Rule 7 of India's "
                "Noise Pollution Rules 2000."
            )
        else:
            action = (
                "This reading is within the legal limit for this zone and time. "
                "No immediate regulatory action is required. If levels increase or "
                "the noise becomes disruptive, start logging readings with timestamps "
                "so you have evidence if a formal complaint becomes necessary later."
            )

    note = "\n\n[Mock response — set LLM_PROVIDER=anthropic or watsonx for AI-generated answers]"
    return f"{action}{note}"


def _generate_anthropic(system_prompt: str, user_prompt: str) -> str:
    import anthropic

    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _generate_watsonx(system_prompt: str, user_prompt: str) -> str:
    """
    Uses the official ibm-watsonx-ai SDK which handles IAM token exchange
    automatically — no manual Bearer token construction needed.
    Requires: pip install ibm-watsonx-ai
    """
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    api_key = os.environ["WATSONX_API_KEY"]
    project_id = os.environ["WATSONX_PROJECT_ID"]
    url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    model_id = os.environ.get("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")

    credentials = Credentials(url=url, api_key=api_key)
    client = APIClient(credentials)
    model = ModelInference(
        model_id=model_id,
        api_client=client,
        project_id=project_id,
        params={"max_new_tokens": 400},
    )
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    result = model.generate_text(prompt=full_prompt)
    return result


def _generate_openrouter(system_prompt: str, user_prompt: str) -> str:
    """
    OpenRouter — OpenAI-compatible API that proxies many models.
    Requires: pip install httpx (already in requirements.txt)
    Set OPENROUTER_API_KEY in .env.
    Optionally override the model with OPENROUTER_MODEL.
    Free-tier models can return empty responses; we retry up to 3 times.
    """
    import httpx, re, time

    api_key = os.environ["OPENROUTER_API_KEY"]
    model   = os.environ.get("OPENROUTER_MODEL", "openrouter/free")

    raw = ""
    for attempt in range(2):
        if attempt:
            time.sleep(1)
        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://noise-assistant",
                    "X-Title": "Noise Pollution Awareness Map",
                },
                json={
                    "model": model,
                    "max_tokens": 400,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            raw  = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            if raw.strip():
                break
        except (httpx.TimeoutException, httpx.HTTPStatusError):
            # On timeout or server error fall through to retry; after last
            # attempt fall back to the rule-based mock so the user gets an answer.
            raw = ""

    if not raw.strip():
        return _generate_mock(system_prompt, user_prompt)

    text = raw.strip()

    # ── Strip thinking/reasoning preamble ─────────────────────────────────────
    # Strategy: work through several patterns from most-specific to generic.

    # 1. Explicit labelled answer block: **Final Answer:** ... or **Output:** ...
    m = re.search(
        r'\*{0,2}(?:final answer|output|answer)\*{0,2}\s*[:\-]\s*(.+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if m:
        return m.group(1).strip().lstrip('"').rstrip('"')

    # 2. Quoted draft: Draft: "..." or Answer: "..."
    m = re.search(
        r'(?:draft|answer)\s*:\s*["\u201c](.+?)["\u201d]',
        text, re.IGNORECASE | re.DOTALL
    )
    if m:
        return m.group(1).strip()

    # 3. Reasoning header present — return first clean prose paragraph that
    #    follows the last numbered step.
    reasoning_headers = (
        r"here.s a thinking process|let me think|check constraints|"
        r"thinking process|reasoning|draft\s*:|analyze user input"
    )
    if re.search(reasoning_headers, text, re.IGNORECASE):
        last_step = None
        for ms in re.finditer(r'^\d+\s*[\.\)]\s', text, re.MULTILINE):
            last_step = ms
        if last_step:
            after = re.split(r'\n{2,}', text[last_step.start():], maxsplit=1)
            if len(after) > 1:
                for para in re.split(r'\n{2,}', after[1]):
                    s = para.strip()
                    if s and not re.match(r'^(\d+\s*[\.\)]\s|\*\*\d|[-*]\s|check )', s, re.IGNORECASE):
                        return s
        # Fallback: return last non-empty paragraph
        paras = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
        for p in reversed(paras):
            if not re.match(r'^(\d+\s*[\.\)]\s|\*\*\d|[-*]\s)', p):
                return p

    return text
