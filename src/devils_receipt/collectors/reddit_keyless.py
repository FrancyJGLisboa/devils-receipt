"""Keyless Reddit source (public search JSON, RSS fallback).

Ported/narrowed from last30days/reddit_keyless.py: tiered keyless discovery,
relevance-floor pruning (shared thresholds), returns [] on the anti-bot wall
(never raises). Implements the source-module contract.

Discovery tiers:
  Tier 0  reddit public search ``.json`` (residential IPs often get 200).
  Tier 1  Reddit RSS keyword search (robust keyless fallback).
"""

from __future__ import annotations

import datetime
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus

from . import http
from .relevance import RELEVANCE_FLOOR, MIN_ON_TOPIC, token_overlap_relevance

# Ag/energy/macro subreddits the roster is curated around. RSS keyword search is
# global; these scope a targeted fallback and label provenance.
COMMODITY_SUBREDDITS = [
    "commodities", "Commodities", "agriculture", "farming", "wallstreetbets",
    "energy", "oil", "options", "investing", "economics",
]

DEPTH_CONFIG = {"quick": 15, "default": 25, "deep": 40}


def _iso(epoch: float | int | None) -> str | None:
    if not epoch:
        return None
    dt = datetime.datetime.fromtimestamp(float(epoch), tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tier0_json(topic: str, limit: int) -> list[dict[str, Any]]:
    url = "https://www.reddit.com/search.json"
    params = {"q": topic, "sort": "relevance", "t": "month", "limit": str(limit)}
    try:
        data = http.get(url, params=params, timeout=20)
    except Exception:
        return []
    posts: list[dict[str, Any]] = []
    for child in (data.get("data", {}).get("children", []) if isinstance(data, dict) else []):
        d = child.get("data", {})
        posts.append({
            "id": "rd_" + (d.get("id") or ""),
            "title": d.get("title") or "",
            "url": "https://www.reddit.com" + (d.get("permalink") or ""),
            "author": d.get("author") or "",
            "body": d.get("selftext") or "",
            "subreddit": d.get("subreddit") or "",
            "published_at": _iso(d.get("created_utc")),
            "date": (_iso(d.get("created_utc")) or "")[:10] or None,
            "engagement": {
                "score": d.get("score") or 0,
                "num_comments": d.get("num_comments") or 0,
            },
        })
    return posts


_ATOM = "{http://www.w3.org/2005/Atom}"


def _tier1_rss(topic: str, limit: int) -> list[dict[str, Any]]:
    url = f"https://www.reddit.com/search.rss?q={quote_plus(topic)}&sort=relevance&t=month&limit={limit}"
    try:
        text = http.get(url, as_json=False, timeout=20)
    except Exception:
        return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    posts: list[dict[str, Any]] = []
    for entry in root.findall(f"{_ATOM}entry"):
        title = (entry.findtext(f"{_ATOM}title") or "").strip()
        link_el = entry.find(f"{_ATOM}link")
        link = link_el.get("href") if link_el is not None else ""
        author = (entry.findtext(f"{_ATOM}author/{_ATOM}name") or "").strip()
        updated = (entry.findtext(f"{_ATOM}updated") or "").strip()
        content = entry.findtext(f"{_ATOM}content") or ""
        body = re.sub(r"<[^>]+>", " ", content)
        sub_match = re.search(r"/r/([A-Za-z0-9_]+)", link or "")
        id_match = re.search(r"/comments/([a-z0-9]+)/", link or "")
        posts.append({
            "id": "rd_" + (id_match.group(1) if id_match else (link or "")),
            "title": title,
            "url": link or "",
            "author": author.replace("/u/", ""),
            "body": body.strip()[:500],
            "subreddit": sub_match.group(1) if sub_match else "",
            "published_at": updated or None,
            "date": updated[:10] if updated else None,
            "engagement": {"score": 0, "num_comments": 0},
        })
    return posts


def search_and_enrich(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> list[dict[str, Any]]:
    limit = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    posts = _tier0_json(topic, limit)
    if not posts:
        posts = _tier1_rss(topic, limit)
    if not posts:
        return []

    # Date filter: keep posts in range or with unknown dates.
    posts = [
        p for p in posts
        if not p.get("date") or (from_date <= p["date"] <= to_date)
    ]

    # Score relevance against title+body.
    for p in posts:
        p["relevance"] = round(token_overlap_relevance(topic, f"{p.get('title','')} {p.get('body','')}"), 2)

    # Relevance floor: strip zero-overlap posts when anything relevant remains.
    on_topic = [p for p in posts if (p.get("relevance") or 0) >= RELEVANCE_FLOOR]
    if len(on_topic) >= MIN_ON_TOPIC:
        posts = on_topic
    else:
        nonzero = [p for p in posts if (p.get("relevance") or 0) > 0]
        if nonzero:
            posts = nonzero

    posts.sort(
        key=lambda p: (
            (p.get("relevance") or 0.0),
            (p.get("engagement", {}).get("score", 0) or 0),
        ),
        reverse=True,
    )
    for i, p in enumerate(posts):
        p["why_relevant"] = f"Reddit discussion in r/{p.get('subreddit','?')}"
    return posts
