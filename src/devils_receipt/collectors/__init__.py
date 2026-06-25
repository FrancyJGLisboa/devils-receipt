"""Vendored keyless source collectors (from commodity-pulse).

Each module implements the same contract:
    search_and_enrich(topic: str, from_date: str, to_date: str, depth="default")
        -> list[dict]  # normalized: id, title, url, author, body, date, engagement, relevance

Vendored verbatim and intentionally self-contained (stdlib only) so this repo
has no path coupling to commodity-pulse. Re-sync by re-copying from
commodity-pulse/skills/commodity-pulse/scripts/lib if the originals improve.
"""
