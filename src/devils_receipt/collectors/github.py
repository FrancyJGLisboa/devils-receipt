"""GitHub keyless source (public repository Search API — ag/energy data + models).

Keyless: GitHub's repository Search API serves UNAUTHENTICATED requests (rate-
limited to ~10/min, ample for one query per run). This is the "what is being
BUILT around this commodity right now" lane — yield models, data pipelines,
trading bots, scrapers — narrative-adjacent signal the social sources miss. It
is keyless-always in the roster (roster.py).

Implements the source-module contract: search_and_enrich(topic, from_date,
to_date, depth) -> list[dict] of normalized items. Returns [] on ANY failure
(rate-limit / network), never raises — graceful degradation.
"""

from __future__ import annotations

from typing import Any

from . import http
from .relevance import token_overlap_relevance

SEARCH_URL = "https://api.github.com/search/repositories"

DEPTH_CONFIG = {"quick": 15, "default": 25, "deep": 40}


def _engagement(repo: dict[str, Any]) -> dict[str, int]:
    return {
        "stars": int(repo.get("stargazers_count") or 0),
        "forks": int(repo.get("forks_count") or 0),
        "open_issues": int(repo.get("open_issues_count") or 0),
    }


def search_and_enrich(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> list[dict[str, Any]]:
    count = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    # Server-side recency bound: `pushed` is the "active right now" signal — a
    # repo not pushed within the window is not live narrative. Keeps the keyless
    # request small so it stays under the unauthenticated rate cap.
    params = {
        "q": f"{topic} pushed:>={from_date}",
        "sort": "updated",
        "order": "desc",
        "per_page": str(count),
    }
    try:
        data = http.get(
            SEARCH_URL,
            params=params,
            headers={"Accept": "application/vnd.github+json"},
            timeout=20,
        )
    except Exception:
        return []

    repos = data.get("items", []) if isinstance(data, dict) else []
    items: list[dict[str, Any]] = []
    for repo in repos:
        full_name = repo.get("full_name") or ""
        description = repo.get("description") or ""
        topics = repo.get("topics") or []
        language = repo.get("language") or ""
        owner = (repo.get("owner") or {}).get("login") or full_name.split("/")[0]
        pushed_at = repo.get("pushed_at")
        # The central entity gate scores title+body; full_name has no spaces, so
        # the commodity token must reach `body` via description + topics.
        body = " ".join(p for p in (description, " ".join(topics)) if p).strip()
        stars = int(repo.get("stargazers_count") or 0)
        items.append({
            "id": f"gh_{repo.get('id')}",
            "title": full_name,
            "url": repo.get("html_url") or "",
            "author": owner,
            "body": body,
            "container": language,
            "published_at": pushed_at,
            "date": pushed_at[:10] if pushed_at else None,
            "engagement": _engagement(repo),
            "relevance": round(token_overlap_relevance(topic, f"{full_name} {body}"), 2),
            "why_relevant": f"GitHub repo ({language or 'repo'}, {stars}★)",
            "metadata": {"repo_id": repo.get("id"), "language": language},
        })
    return items
