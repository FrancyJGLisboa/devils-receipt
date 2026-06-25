#!/usr/bin/env python3
"""Devil's Receipt collector — fetch DISCONFIRMING sources for a belief.

Claude turns a belief into refutation queries (the de Bono Distortion move) and
passes them here. This runs the vendored keyless collectors, dedupes by url,
writes evidence.json (the shape `claimcheck --data` reads), and prints ranked
candidates for Claude to read and cite.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .collectors import github, gnews, hackernews, news_quality, reddit_keyless

# Keyless, topic-agnostic sources only (symbol-mapped ones like StockTwits need
# tickers — wrong for arbitrary beliefs).
SOURCES = {
    "gnews": gnews,
    "reddit": reddit_keyless,
    "hn": hackernews,
    "github": github,
}

# Non-greedy so each match is the span between ADJACENT quote marks — a short
# quote (e.g. "fine") can't desync the pairing and swallow text after it. Length
# is filtered by word count in ungrounded_quotes, not by the regex.
_QUOTE_RE = re.compile(r'["“”]([^"“”]+?)["“”]')

# Source-credibility tier for the memo, so it comes from data not a guess. News
# reuses news_quality (reputable wire / unknown / junk); social + code are flat
# labels — a Reddit post is never a "wire", and the memo should say so.
_NEWS_TIER = {2: "wire", 1: "unknown", 0: "junk"}
_FLAT_TIER = {"reddit": "social", "hn": "social", "github": "code"}


def _tier(item: dict, source: str) -> str:
    return _NEWS_TIER[news_quality.item_tier(item)] if source == "gnews" else _FLAT_TIER[source]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def merge(raw: list[dict]) -> list[dict]:
    """Dedupe by url, drop urlless items, rank relevance-then-recency desc."""
    seen: set[str] = set()
    out: list[dict] = []
    for it in raw:
        url = it.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(it)
    out.sort(key=lambda it: (it.get("relevance") or 0, it.get("date") or ""), reverse=True)
    return out


def ungrounded_quotes(prose: str, items: list[dict], ignore: str | list[str] = ()) -> list[str]:
    """Quotes (>=4 words) in the brief that appear in NO collected item's
    title/body. Empty list == every quote is sourced. This is the real
    provenance gate — claimcheck can't match quotes to sources.

    `ignore` is the belief (or beliefs) the brief restates in quotes; those are
    the thing being refuted, not evidence, so they're not flagged. Whitespace is
    normalized first so line-wrapped quotes match and pair correctly."""
    corpus = " ".join(_norm(f"{it.get('title', '')} {it.get('body', '')}") for it in items)
    skip = {_norm(s) for s in ([ignore] if isinstance(ignore, str) else ignore)}
    bad = []
    for q in _QUOTE_RE.findall(_norm(prose)):
        qn = _norm(q)
        if len(qn.split()) >= 4 and qn not in corpus and qn not in skip:
            bad.append(qn[:60])
    return bad


def collect(queries: list[str], frm: str, to: str, depth: str = "default") -> list[dict]:
    raw: list[dict] = []
    for q in queries:
        for name, mod in SOURCES.items():
            try:
                got = mod.search_and_enrich(q, frm, to, depth)
            except Exception as e:  # collectors should return [], never crash us
                print(f"  ! {name} failed on {q!r}: {e}", file=sys.stderr)
                continue
            for it in got:
                it["query"], it["source"] = q, name
                it["tier"] = _tier(it, name)
                raw.append(it)
    return merge(raw)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Collect disconfirming sources for a belief.")
    ap.add_argument("--queries", help="semicolon-separated refutation queries")
    ap.add_argument("--from", dest="frm", help="YYYY-MM-DD window start")
    ap.add_argument("--to", help="YYYY-MM-DD window end")
    ap.add_argument("--depth", default="default", choices=["quick", "default", "deep"])
    ap.add_argument("--out", default="evidence.json")
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args(argv)
    if not (a.queries and a.frm and a.to):
        ap.error("--queries, --from, --to are required")

    queries = [q.strip() for q in a.queries.split(";") if q.strip()]
    items = collect(queries, a.frm, a.to, a.depth)[: a.limit]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"window": [a.frm, a.to], "items": items}, ensure_ascii=False, indent=2)
    )
    print(f"{len(items)} candidate(s) -> {a.out}\n")
    for it in items:
        print(f"[{it['source']}/{it.get('tier', '?')}] {it.get('date', '?')}  {it.get('title', '')}")
        print(f"    {it['url']}")
        body = _norm(it.get("body", ""))
        if body:
            print(f"    {body[:200]}")
    if not items:
        print("NO disconfirming candidates found. Emit the honest-null statement.")
    return 0
