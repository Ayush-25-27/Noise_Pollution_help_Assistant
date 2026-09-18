# AGENTS.md

Persistent context for IBM Bob. This file is read automatically at the
start of every Bob conversation in this project, so Bob doesn't need
to rediscover the codebase each time.

## What this project is

Noise Pollution Awareness Map — an agentic + generative AI backend for
the 1M1B AI for Sustainability Virtual Internship (SDG 11). It takes a
decibel reading + zone type, checks it against the real legal noise
limit, guesses the likely source, and generates a plain-language report
grounded in retrieved regulation text.

## Architecture — read this before changing anything

Request flow: `frontend/index.html` → `app/api/routes.py` →
`app/agent/orchestrator.py` → tools → `app/agent/llm_client.py` → response.

The orchestrator (`app/agent/orchestrator.py`) is the only file that
decides *which* tools run and in what order. Individual tools never call
each other directly — they're only ever called by the orchestrator. Keep
it that way; it's what makes this "agentic" rather than one big script.

## Hard rule: keep classification deterministic

`app/agent/tools/classification_tool.py` (legal-limit check + source
inference) must stay plain rule-based Python — no LLM call, ever. This
is intentional: the tool's whole purpose is to produce evidence a
resident can cite to a ward office, so the same input must always
produce the same output. If asked to "make the classification smarter
with AI," push back and suggest improving the rule table instead, or
adding a *separate* optional ML classifier behind a flag — don't fold
it into this file.

## Where generation is allowed

Only `app/agent/llm_client.py`'s `generate()` should ever call a
language model. It has three backends behind `LLM_PROVIDER`:
`mock` (default, no key needed), `anthropic`, `watsonx`. Never call an
LLM API directly from another file — route everything through
`generate()` so the provider stays swappable.

## RAG corpus

`app/rag/sources/regulations.json` holds six short, hand-written
summary passages about noise-zone regulations (not copied from any
single external source). `app/rag/vector_store.py` does TF-IDF +
cosine similarity search over them — deliberately lightweight, sized
for a handful of passages, not a production-scale corpus. If asked to
scale this up to real WHO/CPCB document text, swap in real embeddings
+ Chroma/FAISS here; the `rag_retrieval_tool.py` interface it's called
through should not need to change.

## Folder map

```
app/
  main.py              FastAPI entrypoint, mounts frontend + API routes
  agent/
    orchestrator.py    the agent decision loop — start here
    llm_client.py       pluggable generation backend
    tools/               classification_tool, noise_fetch_tool, rag_retrieval_tool
    prompts/              system_prompt.md, report_prompt.md
  rag/                   vector_store.py + sources/regulations.json
  models/schemas.py     request/response shapes (Pydantic)
  api/routes.py          thin HTTP layer, no logic of its own
frontend/index.html      plain HTML/JS calling /api/report
data/sample_noise_readings.json   offline fallback data
evaluation/test_cases.md          manual QA checklist
docs/                    blueprint deck + tech stack writeup (reference only, not code)
```

## Conventions

- Every tool function takes plain arguments and returns a plain dict —
  no custom classes passed between files, to keep tool signatures easy
  for an agent (human or AI) to read at a glance.
- Never surface a specific individual, household, or business name in
  generated text — this system is for location/pattern-level advocacy,
  not personal accusation. This constraint lives in `system_prompt.md`;
  don't weaken it.
- Run `python3 -m app.agent.orchestrator` for a quick end-to-end sanity
  check without starting the full server.
- Full server: `uvicorn app.main:app --reload --port 8000`.

## What's still a placeholder / known gap

`noise_fetch_tool.py` reads from a local JSON file, not a live
crowdsourcing API — there's no public "OpenAQ-equivalent" for noise
data yet. If building this out further, that's the most valuable real
integration to add.
