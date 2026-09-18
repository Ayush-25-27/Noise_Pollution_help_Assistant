"""
web_search_tool.py

Fetches live web snippets for a query so Xaya can answer questions that need
real-world numbers (e.g. "total noise complaints filed in India").

Strategy (no API key required):
  1. DuckDuckGo Instant Answer API  — abstract text + related topics (JSON).
  2. Wikipedia REST API             — search + page summary for factual topics.
  3. DuckDuckGo /lite HTML scrape   — organic result snippets as last resort.

Returns a list of short text snippets with their sources so the caller can
inject them into the LLM prompt.  Returns [] on total failure — callers must
handle an empty list gracefully.
"""

import re
import urllib.parse


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for `query` and return up to `max_results` snippets.

    Each result:  { "title": str, "snippet": str, "url": str }
    """
    results: list[dict] = []

    # 1. DuckDuckGo Instant Answer (JSON, fast, no key)
    try:
        results.extend(_ddg_instant(query))
    except Exception:
        pass

    # 2. Wikipedia REST search (very reliable for stats / background)
    if len(results) < max_results:
        try:
            results.extend(_wikipedia(query, max_results))
        except Exception:
            pass

    # 3. DuckDuckGo /lite scrape fallback
    if len(results) < max_results:
        try:
            results.extend(_ddg_lite(query, max_results))
        except Exception:
            pass

    # Deduplicate by first 80 chars of snippet
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        key = r["snippet"][:80]
        if key not in seen and r["snippet"].strip():
            seen.add(key)
            deduped.append(r)

    return deduped[:max_results]


# ── DuckDuckGo Instant Answer API ─────────────────────────────────────────────

def _ddg_instant(query: str) -> list[dict]:
    import httpx

    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
        "t": "noise-assistant",
    }
    headers = {"User-Agent": "noise-assistant/1.0 (educational project)"}
    resp = httpx.get(
        "https://api.duckduckgo.com/",
        params=params,
        headers=headers,
        timeout=8,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()

    out: list[dict] = []

    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        out.append({
            "title": data.get("Heading") or query,
            "snippet": abstract,
            "url": data.get("AbstractURL") or "",
        })

    answer = (data.get("Answer") or "").strip()
    if answer:
        out.append({"title": "Quick answer", "snippet": answer, "url": ""})

    for topic in (data.get("RelatedTopics") or [])[:3]:
        text = (topic.get("Text") or "").strip()
        if text:
            out.append({
                "title": topic.get("Name") or query,
                "snippet": text,
                "url": topic.get("FirstURL") or "",
            })

    return out


# ── Wikipedia REST API ────────────────────────────────────────────────────────

def _wikipedia(query: str, max_results: int) -> list[dict]:
    """
    Uses Wikipedia's public REST API:
      1. /w/api.php  search → find best matching article title
      2. /api/rest_v1/page/summary/{title} → get the extract (first 2 sentences)
    """
    import httpx

    # Wikimedia requires a descriptive User-Agent per their bot policy
    headers = {
        "User-Agent": (
            "noise-assistant/1.0 (https://github.com/noise-assistant; "
            "educational-project) python-httpx"
        )
    }

    # Step 1 — search
    search_url = "https://en.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": min(max_results, 3),
        "format": "json",
        "utf8": "1",
    }
    resp = httpx.get(search_url, params=search_params, headers=headers, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("query", {}).get("search", [])

    out: list[dict] = []
    for hit in hits[:2]:
        title = hit.get("title", "")
        snippet_raw = hit.get("snippet", "")
        snippet = _strip_tags(snippet_raw)
        page_url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))

        if not snippet:
            continue

        # Step 2 — get richer summary for the top hit
        if not out:
            try:
                sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                sr = httpx.get(sum_url, headers=headers, timeout=8)
                if sr.status_code == 200:
                    extract = sr.json().get("extract", "")
                    # Take first ~400 chars
                    if extract:
                        snippet = extract[:500].rsplit(" ", 1)[0] + "…"
            except Exception:
                pass

        out.append({"title": title, "snippet": snippet, "url": page_url})

    return out


# ── DuckDuckGo /lite HTML scrape ──────────────────────────────────────────────

def _ddg_lite(query: str, max_results: int) -> list[dict]:
    """
    Hits https://lite.duckduckgo.com/lite/ — a minimal HTML page that is
    less aggressively bot-guarded than the main site.
    """
    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": "https://lite.duckduckgo.com/",
    }
    data = {"q": query, "kl": "in-en", "s": "0", "dc": "1", "v": "l", "o": "json", "api": "d.js"}
    resp = httpx.post(
        "https://lite.duckduckgo.com/lite/",
        data=data,
        headers=headers,
        timeout=10,
        follow_redirects=True,
    )
    resp.raise_for_status()
    html = resp.text

    out: list[dict] = []

    # lite page uses a table; each result row has a link <a class="result-link"> and
    # a snippet in the next <td class="result-snippet">
    link_re    = re.compile(r'class="result-link"[^>]*href="([^"]+)"[^>]*>([^<]+)<')
    snippet_re = re.compile(r'class="result-snippet"[^>]*>(.*?)</td>', re.DOTALL)

    links   = link_re.findall(html)
    snips   = snippet_re.findall(html)

    for (url, title), snip_html in zip(links, snips):
        snip = _strip_tags(snip_html).strip()
        if snip:
            out.append({"title": title.strip(), "snippet": snip, "url": url})
        if len(out) >= max_results:
            break

    return out


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", text).strip()
