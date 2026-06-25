"""Google News RSS source (keyless news spine — market-narrative wire).

Google News exposes a keyless RSS search endpoint that aggregates the commodity
news wires (Reuters, Bloomberg, AgWeb, Pro Farmer, DTN, …) as dated, publisher-
attributed items. This is the narrative spine of the senior-analyst report — and
it doubles as the DRIVER-BUCKETING mechanism: query it once per driver (weather /
exports / supply / policy / positioning) and each bucket is known by construction
(see synthesis layer), no fragile post-hoc classification.

Implements the source-module contract. Returns [] on any failure, never raises.
News carries no engagement counts; items are ranked by recency + relevance, not
votes — engagement is intentionally empty.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus

from . import http, news_quality
from .relevance import token_overlap_relevance

SEARCH_URL = "https://news.google.com/rss/search"

DEPTH_CONFIG = {"quick": 10, "default": 20, "deep": 35}

_TAG_RE = re.compile(r"<[^>]+>")


def _iso(pubdate: str | None) -> str | None:
    if not pubdate:
        return None
    try:
        return parsedate_to_datetime(pubdate).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def _strip_suffix(title: str, publisher: str) -> str:
    """Google News titles end with ' - <Publisher>'; drop it for a clean lede."""
    if publisher and title.endswith(f" - {publisher}"):
        return title[: -(len(publisher) + 3)].strip()
    return title


def search_and_enrich(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
) -> list[dict[str, Any]]:
    limit = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    url = f"{SEARCH_URL}?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
    try:
        text = http.get(url, as_json=False, timeout=20)
    except Exception:
        return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    items: list[dict[str, Any]] = []
    for entry in root.findall(".//item"):
        raw_title = (entry.findtext("title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        published_at = _iso(entry.findtext("pubDate"))
        date = published_at[:10] if published_at else None
        # Drop items outside the recency window (undated items are kept; the
        # report-level recency filter is the backstop).
        if date and not (from_date <= date <= to_date):
            continue
        src_el = entry.find("source")
        publisher = (src_el.text or "").strip() if src_el is not None else ""
        publisher_url = src_el.get("url") if src_el is not None else None
        title = _strip_suffix(raw_title, publisher)
        body = _TAG_RE.sub(" ", entry.findtext("description") or "").strip()[:600]
        relevance = token_overlap_relevance(topic, f"{title} {body}")
        items.append({
            "id": "gn_" + (link.rsplit("/", 1)[-1] or raw_title)[:48],
            "title": title,
            "url": link,
            "author": publisher,
            "body": body,
            "container": publisher,
            "published_at": published_at,
            "date": date,
            "engagement": {},
            "relevance": round(relevance, 2),
            "why_relevant": f"{publisher or 'News'} via Google News",
            "metadata": {"publisher": publisher, "publisher_url": publisher_url},
        })

    # Reliability pass: dedup republished copy, drop SEO-junk, rank reputable
    # wires above unknowns (recency-first). Replaces the plain recency sort.
    items = news_quality.prioritize(items)
    return items[:limit]
