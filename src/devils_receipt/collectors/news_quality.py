"""News reliability tier — promote reputable wires, drop SEO-chum, dedup.

The price (Yahoo) and positioning (CFTC) anchors are authoritative; the news lane
is the weak leg — Google News returns reputable wires (Reuters, AgWeb, Pro Farmer)
intermixed with SEO aggregators (newsline.com, HarianBasis.co) at equal rank. This
module hardens it WITHOUT fabricating anything: it ranks by publisher reputation,
drops known junk when better items exist, and collapses duplicate stories.

Tiers: 2 = reputable wire/trade press, 1 = unknown (kept, ranked below), 0 = junk
(dropped when any non-junk remains; kept only if EVERYTHING is junk — never nuke a
thin brief). Ranking stays recency-first; tier breaks ties within a day.
"""

from __future__ import annotations

import re
from typing import Any

TIER_REPUTABLE = 2
TIER_UNKNOWN = 1
TIER_JUNK = 0

# Registrable domains we trust (ag + energy + macro wires & established trade press).
# Matched as a suffix, so sub.agweb.com still resolves to agweb.com.
REPUTABLE_DOMAINS: frozenset[str] = frozenset({
    # wires / general
    "reuters.com", "bloomberg.com", "apnews.com", "wsj.com", "ft.com",
    "cnbc.com", "marketwatch.com", "barrons.com",
    # ag trade
    "agweb.com", "dtnpf.com", "profarmer.com", "brownfieldagnews.com",
    "agriculture.com", "agweek.com", "farmprogress.com", "world-grain.com",
    "agricensus.com", "agrimoney.com", "feedstuffs.com", "successfulfarming.com",
    "farmdocdaily.illinois.edu", "ag.purdue.edu",
    # energy
    "oilprice.com", "eia.gov", "spglobal.com", "argusmedia.com", "rigzone.com",
    "naturalgasintel.com", "hellenicshippingnews.com", "gcaptain.com",
    # market data
    "barchart.com",
})

# Known low-quality SEO / scraper aggregators observed in real runs. Small and
# explicit on purpose — we promote known-good and drop known-bad, never guess.
JUNK_DOMAINS: frozenset[str] = frozenset({
    "newsline.com", "harianbasis.co",
})

# Name fallbacks when a publisher URL is missing (Google News <source> text).
_REPUTABLE_NAME_HINTS = (
    "reuters", "bloomberg", "associated press", "wall street journal",
    "financial times", "agweb", "dtn", "progressive farmer", "pro farmer",
    "brownfield", "successful farming", "world-grain", "world grain",
    "s&p global", "platts", "argus", "oilprice", "rigzone", "barchart",
    "hellenic shipping", "gcaptain", "cnbc", "marketwatch", "agrimoney",
    "agricensus", "farmdoc",
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def _domain(url: str | None) -> str:
    if not url:
        return ""
    host = re.sub(r"^[a-z]+://", "", url.strip().lower())
    host = host.split("/", 1)[0].split("?", 1)[0]
    return host[4:] if host.startswith("www.") else host


def _suffix_match(host: str, domains: frozenset[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def item_tier(item: dict[str, Any]) -> int:
    """Reputation tier for a gnews item (2 reputable / 1 unknown / 0 junk)."""
    host = _domain((item.get("metadata") or {}).get("publisher_url"))
    name = str(item.get("container") or item.get("author") or "").lower()
    if host:
        if _suffix_match(host, JUNK_DOMAINS):
            return TIER_JUNK
        if _suffix_match(host, REPUTABLE_DOMAINS):
            return TIER_REPUTABLE
    if any(hint in name for hint in _REPUTABLE_NAME_HINTS):
        return TIER_REPUTABLE
    return TIER_UNKNOWN


def dedup_key(title: str) -> str:
    """Normalized headline for near-duplicate detection (case/punct-insensitive)."""
    return " ".join(_WORD_RE.findall((title or "").lower()))


def _rank(item: dict[str, Any]) -> tuple:
    # recency-first; tier breaks same-day ties; relevance last.
    return (item.get("date") or "", item_tier(item), item.get("relevance") or 0.0)


def _dedup(items: list[dict[str, Any]], key_of) -> list[dict[str, Any]]:
    """Collapse items sharing key_of(item), keeping the best-ranked of each."""
    best: dict[str, dict[str, Any]] = {}
    for it in items:
        key = key_of(it)
        cur = best.get(key)
        if cur is None or _rank(it) > _rank(cur):
            best[key] = it
    return list(best.values())


def prioritize(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedup, drop junk (unless all junk), and rank reputable-first within a day.

    Pure/deterministic; preserves each kept item's real publisher + URL.
    """
    # 1a. Collapse exact-URL dupes, then 1b. republished copy (same headline,
    #     different outlet). Keeping the best-ranked survivor of each (so the
    #     reputable outlet wins over a blog that reran the same wire story).
    deduped = _dedup(items, lambda it: it.get("url") or dedup_key(it.get("title", "")))
    deduped = _dedup(deduped, lambda it: dedup_key(it.get("title", "")) or (it.get("url") or ""))

    # 2. Drop junk only when something better survives (never nuke a thin brief).
    non_junk = [it for it in deduped if item_tier(it) > TIER_JUNK]
    kept = non_junk if non_junk else deduped

    # 3. Reputable-first within the same day, most-recent first overall.
    kept.sort(key=_rank, reverse=True)
    return kept
