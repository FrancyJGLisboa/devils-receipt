#!/usr/bin/env python3
"""Loss-function eval for Devil's Receipt — the deterministic checks.

Run: `uv run python evals/run_eval.py` (claimcheck checks need
`uv pip install -e ../claimcheck`; they SKIP, not fail, if it's absent).

Semantic checks (zero-confirmation, relevance) are judged live on the real brief
and are not in here — faking them deterministically would be dishonest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from devils_receipt.refute import ungrounded_quotes  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
MARKER = "No refutation found ≠ confirmed."
WINDOW = ("2026-05-25", "2026-06-25")

results: list[tuple[str, bool | None, str]] = []


def record(name: str, ok: bool | None, note: str = "") -> None:
    results.append((name, ok, note))


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def honest_null_ok(brief: str, items: list) -> bool:
    """When no evidence survived, the brief must carry the no-refutation marker."""
    return MARKER in brief if not items else True


# 1. Provenance — good brief fully grounded, fabricated brief caught.
BELIEF = "Brazil's safrinha corn is fine this year"
ev = load("evidence_sample.json")["items"]
good = (FIX / "brief_good.md").read_text()
fab = (FIX / "brief_fabricated.md").read_text()
record("provenance: good brief grounded", ungrounded_quotes(good, ev, ignore=BELIEF) == [])
record("provenance: fabricated quote caught", ungrounded_quotes(fab, ev, ignore=BELIEF) != [])

# 2. Honest-null — empty evidence requires the marker; missing marker rejected.
null_brief = (FIX / "brief_null.md").read_text()
record("honest-null: marker present on empty evidence", honest_null_ok(null_brief, []))
record("honest-null: missing marker rejected", honest_null_ok("nothing here", []) is False)

# 3 & 4. claimcheck integrity (date gate) + receipt round-trip.
try:
    from claimcheck import check
    from claimcheck.receipt import build_receipt, verify_receipt
except ImportError:
    record("claimcheck: date gate", None, "claimcheck not installed — `uv pip install -e ../claimcheck`")
    record("claimcheck: receipt round-trip", None, "claimcheck not installed")
else:
    data = load("evidence_sample.json")
    in_window = check(good, data, window=WINDOW, has_quotes=True)
    record("date gate: in-window brief clean",
           not any(f["rule"] == "date-out-of-window" for f in in_window))
    stale = check("As reported on 2026-01-01, the crop failed.", data, window=WINDOW, has_quotes=True)
    record("date gate: stale date flagged",
           any(f["rule"] == "date-out-of-window" for f in stale))

    receipt = build_receipt(str(FIX / "evidence_sample.json"), str(FIX / "brief_good.md"),
                            [{"level": "info", "rule": "devils-receipt", "term": "signed"}])
    clean = verify_receipt(receipt, str(FIX / "evidence_sample.json"),
                           str(FIX / "brief_good.md"), None)
    record("receipt: round-trip verifies", clean == [])
    tampered = verify_receipt(receipt, str(FIX / "evidence_sample.json"),
                              str(FIX / "brief_fabricated.md"), None)
    record("receipt: tampered prose fails", tampered != [])

# Report
failed = 0
for name, ok, note in results:
    tag = "PASS" if ok else ("SKIP" if ok is None else "FAIL")
    if ok is False:
        failed += 1
    print(f"  [{tag}] {name}" + (f"  — {note}" if note else ""))
print(f"\n{sum(1 for _, o, _ in results if o)} pass, {failed} fail, "
      f"{sum(1 for _, o, _ in results if o is None)} skip")
sys.exit(1 if failed else 0)
