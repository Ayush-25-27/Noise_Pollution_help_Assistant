# Noise Pollution Awareness Map — Tech Stack & AI Components

## 1. Recommended tech stack

| Layer | Tool | Why |
|---|---|---|
| Frontend | React or plain HTML/JS | Same lightweight approach as the AQI prototype |
| Backend / API | Python + FastAPI | Simple to wire up model calls and tools |
| LLM | IBM Granite via watsonx.ai, or Claude via Anthropic API | Granite is explicitly listed as an allowed component |
| Agent framework | LangChain/LlamaIndex agent, or IBM watsonx Orchestrate | Orchestrates the multi-tool decision flow below |
| RAG / vector store | ChromaDB or FAISS + embeddings (or lightweight TF-IDF for a student-scale corpus) | Grounds source classification and legal-limit answers in real noise-regulation text |
| Reference data | India's Noise Pollution (Regulation and Control) Rules limits, WHO environmental noise guidelines | Gives the model actual legal thresholds instead of inventing them |
| Database (optional) | SQLite/Postgres | Stores logged readings for the community map / advocacy report |
| Deployment | Render, Railway, or IBM Cloud Code Engine | Free tiers, easy to demo |

## 2. Folder structure

```
noise-assistant/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py
│   ├── agent/
│   │   ├── orchestrator.py        # decides which tools to call
│   │   ├── llm_client.py          # pluggable mock/anthropic/watsonx backend
│   │   ├── tools/
│   │   │   ├── noise_fetch_tool.py       # crowdsourced/sample reading lookup
│   │   │   ├── classification_tool.py    # deterministic dB -> zone-limit + source inference
│   │   │   └── rag_retrieval_tool.py     # noise-regulation passage retrieval
│   │   └── prompts/
│   │       ├── system_prompt.md
│   │       └── report_prompt.md
│   ├── rag/
│   │   ├── vector_store.py
│   │   └── sources/regulations.json
│   ├── models/schemas.py
│   └── api/routes.py
├── frontend/index.html
├── data/sample_noise_readings.json
├── evaluation/test_cases.md
└── Dockerfile
```

## 3. AI components — generative vs. agentic

### Generative AI components

| Component | Role |
|---|---|
| Prompt engineering | System prompt constrains the model to never name individuals/households and always cite the applicable legal limit |
| IBM Granite / Claude | Writes the plain-language advocacy-style report from structured tool outputs |
| RAG | Grounds every answer in the actual zone-type decibel limits, not invented thresholds |
| Summarization | Condenses multiple logged readings into one community-level report an RWA or ward office can act on |

### Agentic AI components

| Component | Role |
|---|---|
| Agent orchestrator | Decides: do we have a reading already, or fetch one? Do we need the regulation lookup for this zone type? |
| Tool: noise data fetch | Retrieves a logged/crowdsourced reading, falling back to sample data if none exists |
| Tool: classification | Deterministic dB \u2192 legal-limit-exceedance check, plus a rule-based source-inference heuristic (time-of-day + duration pattern) \u2014 kept non-LLM on purpose, same reasoning as the AQI project's classifier |
| Tool: RAG retrieval | Looks up the correct legal limit and guidance for the stated zone type |
| Multi-step reasoning | For "what can I do with this reading," the agent chains: classify \u2192 check exceedance \u2192 retrieve advocacy guidance \u2192 generate the final answer |

**Why keep source inference rule-based, not purely LLM-guessed:** whether a pattern looks like "construction" vs "traffic" is a testable heuristic (duration, time-of-day, steadiness) — keeping it deterministic means the classification is defensible if someone ever challenges the report, which matters for a tool whose whole point is being *evidence*.
