# 🔊 Noise Pollution Awareness Map

An **agentic + generative AI** backend for the **1M1B AI for Sustainability Virtual Internship (SDG 11)**. The system takes a decibel reading and zone type, checks it against India's legal noise limits, infers the likely source, retrieves regulation passages, and generates a plain-language advisory report — all in a single API call.

---

## Highlights

- **Deterministic classification** — legal-limit checks are pure rule-based Python (never LLM), so the same input always produces the same, citable verdict.
- **Pluggable LLM backends** — switch between `mock` (offline), `anthropic` (Claude), `watsonx` (IBM Granite), or `openrouter` with one env-var change.
- **Lightweight RAG** — TF-IDF + cosine similarity over hand-curated regulation passages; no external vector DB required.
- **Agentic orchestration** — a decision loop fetches missing readings, runs classification, retrieves passages, and generates the final report.
- **Responsible AI** — responses never name individuals; all claims include the applicable legal limit and the `over_by` margin so every statement is checkable.
- **Chat interface (Xaya)** — a conversational assistant endpoint (`/api/chat`) answers free-text noise questions, with optional live web search fallback.

---

## How It Works

```
User request
     │
     ▼
POST /api/report  ──►  orchestrator.py
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       noise_fetch_tool  classification   rag_retrieval_tool
       (get reading)     _tool            (regulation passages)
                         (dB → limit)
                             │
                             ▼
                        llm_client.generate()
                        (mock / anthropic / watsonx / openrouter)
                             │
                             ▼
                       JSON response
```

1. **Fetch** — if `db`, `time_of_day`, or `duration` are omitted, `noise_fetch_tool` looks them up from sample/crowdsourced data.
2. **Classify** — `classification_tool` checks the reading against India's zone-type limits (deterministic, never LLM).
3. **Retrieve** — `rag_retrieval_tool` pulls the most relevant regulation passages for the zone and any free-text question.
4. **Generate** — `llm_client.generate()` produces a 3–5 sentence plain-language advisory, grounded in the tool outputs.

---

## Legal Noise Limits (India — Noise Pollution Rules 2000)

| Zone | Day limit | Night limit |
|---|---|---|
| Silence (school / hospital / court) | 50 dB | 40 dB |
| Residential | 55 dB | 45 dB |
| Commercial | 65 dB | 55 dB |
| Industrial | 75 dB | 70 dB |

---

## API Reference

### `POST /api/report`

Generate a noise pollution report.

**Request body**

```json
{
  "location": "Near Lotus Public School, Sector 12",
  "zone": "silence",
  "db": 78,
  "time_of_day": "night",
  "duration": "sustained",
  "question": "What can I do with this reading?"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `location` | string | ✅ | Free-text location description |
| `zone` | `residential` \| `silence` \| `commercial` \| `industrial` | ✅ | |
| `db` | integer 0–200 | ❌ | If omitted, fetched from sample data |
| `time_of_day` | `day` \| `night` | ❌ | If omitted, fetched from sample data |
| `duration` | `brief` \| `sustained` | ❌ | If omitted, fetched from sample data |
| `question` | string | ❌ | Optional free-text follow-up |

**Response body**

```json
{
  "location": "Near Lotus Public School, Sector 12",
  "zone": "silence",
  "zone_label": "a silence zone (school/hospital)",
  "db": 78,
  "time_of_day": "night",
  "duration": "sustained",
  "data_source": "user_provided",
  "limit": 40,
  "exceeds": true,
  "over_by": 38,
  "source_guess": "a sustained nighttime source — likely a generator, late-running machinery, or an ongoing event",
  "regulation_passages": ["..."],
  "answer": "..."
}
```

### `POST /api/chat`

Conversational interface (Xaya). Accepts a free-text message and returns a plain-language reply.

```json
{ "message": "What is the noise limit near a hospital?" }
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Leave `.env` as-is (`LLM_PROVIDER=mock`) to run **fully offline** with no API keys.

### 3. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** for the frontend, or hit the API directly:

```bash
curl -s -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d '{"location":"Near Lotus Public School, Sector 12","zone":"silence","db":78,"time_of_day":"night","duration":"sustained","question":"What can I do with this?"}' \
  | python3 -m json.tool
```

### 4. Quick sanity check (no server needed)

```bash
python3 -m app.agent.orchestrator
```

---

## LLM Backends

Set `LLM_PROVIDER` in `.env` to switch providers. All generation is routed through `llm_client.generate()` — no LLM calls anywhere else.

| Provider | `LLM_PROVIDER` | Keys needed |
|---|---|---|
| Mock (offline, rule-based) | `mock` | None |
| Claude (Anthropic) | `anthropic` | `ANTHROPIC_API_KEY` |
| IBM Granite (watsonx.ai) | `watsonx` | `WATSONX_API_KEY`, `WATSONX_PROJECT_ID` |
| OpenRouter (many models) | `openrouter` | `OPENROUTER_API_KEY` |

**Anthropic (Claude)**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# Optional: ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**IBM Granite via watsonx.ai**
```env
LLM_PROVIDER=watsonx
WATSONX_API_KEY=...
WATSONX_PROJECT_ID=...
# Optional: WATSONX_URL=https://us-south.ml.cloud.ibm.com
#           WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
```

**OpenRouter (free-tier Llama 3.1 by default)**
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=...
# Optional: OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
```

---

## Project Structure

```
noise-assistant/
├── app/
│   ├── main.py                          # FastAPI entrypoint — mounts frontend + API routes
│   ├── agent/
│   │   ├── orchestrator.py              # Agent decision loop — start here
│   │   ├── llm_client.py                # Pluggable mock / anthropic / watsonx / openrouter
│   │   ├── tools/
│   │   │   ├── classification_tool.py   # Deterministic dB → limit check + source inference
│   │   │   ├── noise_fetch_tool.py      # Reading lookup (sample data fallback)
│   │   │   ├── rag_retrieval_tool.py    # TF-IDF regulation passage retrieval
│   │   │   └── web_search_tool.py       # DuckDuckGo live search (chat endpoint)
│   │   └── prompts/
│   │       ├── system_prompt.md         # LLM constraints and framing rules
│   │       └── report_prompt.md         # Structured report template
│   ├── rag/
│   │   ├── vector_store.py              # TF-IDF + cosine similarity
│   │   └── sources/regulations.json    # Hand-curated regulation passages
│   ├── models/schemas.py                # Pydantic request / response shapes
│   └── api/routes.py                    # Thin HTTP layer — no business logic
├── frontend/index.html                  # Plain HTML/JS frontend
├── data/sample_noise_readings.json      # Offline fallback readings
├── evaluation/test_cases.md             # Manual QA checklist
├── tests/                               # Pytest suite
├── docs/                                # Blueprint deck + tech stack writeup
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Running Tests

```bash
pytest tests/
```

The test suite covers the API endpoints, the classification tool, and the orchestrator end-to-end.

---

## Deployment

### Render.com

1. Push to GitHub.
2. **New → Web Service** → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add `.env` variables under **Environment**, then deploy.

### Docker (any host, including IBM Cloud Code Engine)

```bash
docker build -t noise-assistant .
docker run -p 8000:8000 --env-file .env noise-assistant
```

---

## Responsible AI

| Principle | How it's enforced |
|---|---|
| **Fairness** | Every exceedance verdict includes the exact legal limit and `over_by` margin — no blanket "loud = bad" judgment |
| **Transparency** | `limit`, `over_by`, and `regulation_passages` are always returned so any claim is checkable |
| **Privacy** | Schema never asks for or stores a name, phone number, or precise home address — only a general location string |
| **Ethics** | `system_prompt.md` hard-constrains the LLM to never name or imply blame toward a specific individual or household |
| **Determinism** | Legal-limit classification is pure rule-based Python — the same input always produces the same citable verdict |

---

## SDG 11 Connection

This project supports **UN Sustainable Development Goal 11 — Sustainable Cities and Communities**. Noise pollution is an underreported urban health hazard; this tool gives residents evidence-grade readings they can take to a Pollution Control Board, RWA, or ward office without needing legal or technical expertise.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend / API | Python 3.11+, FastAPI, Uvicorn |
| AI / LLM | IBM Granite (watsonx.ai) · Claude (Anthropic) · OpenRouter |
| RAG | TF-IDF + cosine similarity (scikit-learn) |
| Data validation | Pydantic v2 |
| Frontend | Plain HTML + JavaScript |
| Containerisation | Docker |
| Testing | pytest |
