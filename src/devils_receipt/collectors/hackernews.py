"""Hacker News keyless source (Algolia API — free, no auth).

Ported/narrowed from last30days/hackernews.py. Implements the source-module
contract: search_and_enrich(topic, from_date, to_date, depth) -> list[dict] of
normalized items with url / title / body / author / published_at / engagement.
"""

from __future__ import annotations

import datetime
import math
from typing import Any

from . import http
from .relevance import token_overlap_relevance

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

DEPTH_CONFIG = {"quick": 15, "default": 30, "deep": 60}


def _date_to_unix(date_str: str) -> int:
    y, m, d = (int(x) for x in date_str.split("-"))
    dt = datetime.datetime(y, m, d, tzinfo=datetime.timezone.utc)
    return int(dt.timestamp())


def _unix_to_iso(ts: int) -> str:
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def search_and_enrich(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> list[dict[str, Any]]:
    count = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    from_ts = _date_to_unix(from_date)
    to_ts = _date_to_unix(to_date) + 86400

    tokens = topic.replace(",", " ").replace("-", " ").split()
    params = {
        "query": " ".join(tokens),
        "tags": "story",
        "numericFilters": f"created_at_i>{from_ts},created_at_i<{to_ts},points>1",
        "hitsPerPage": str(count),
    }
    if len(tokens) > 1:
        params["optionalWords"] = " ".join(tokens[1:])

    try:
        response = http.get(ALGOLIA_SEARCH_URL, params=params, timeout=30)
    except Exception:
        return []

    hits = response.get("hits", []) if isinstance(response, dict) else []
    items: list[dict[str, Any]] = []
    for i, hit in enumerate(hits):
        object_id = hit.get("objectID", "")
        points = hit.get("points") or 0
        num_comments = hit.get("num_comments") or 0
        created_at_i = hit.get("created_at_i")
        published_at = _unix_to_iso(created_at_i) if created_at_i else None

        title = hit.get("title") or hit.get("story_title") or ""
        article_url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"

        rank_score = max(0.3, 1.0 - (i * 0.02))
        engagement_boost = min(0.2, math.log1p(points) / 40)
        content_score = token_overlap_relevance(topic, title)
        relevance = min(1.0, 0.6 * rank_score + 0.4 * content_score + engagement_boost)

        items.append({
            "id": f"hn_{object_id}",
            "title": title,
            "url": article_url,
            "author": hit.get("author") or "",
            "body": title,
            "published_at": published_at,
            "date": published_at[:10] if published_at else None,
            "engagement": {"points": points, "comments": num_comments},
            "relevance": round(relevance, 2),
            "why_relevant": f"HN story: {title[:60]}",
            "metadata": {"hn_id": object_id},
        })
    return items
