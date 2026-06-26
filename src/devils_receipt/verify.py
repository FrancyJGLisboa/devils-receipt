#!/usr/bin/env python3
"""Live provenance gate — every quote in the memo must appear in a collected source.

claimcheck guards against invented figures/dates and tampering, but with `--quotes`
its quote check is off. This is the check that actually verifies quotes are real:
it reuses `ungrounded_quotes` (the same function the eval tests) against the live
brief + evidence. Run it in Step 4 alongside claimcheck.

    python -m devils_receipt.verify --prose brief.md --data evidence.json \
        --thesis "Brazil's safrinha corn is fine this year"

Exit 1 if any >=4-word quote is not grounded in some collected item; 0 otherwise.
The thesis is excluded — the memo restating the claim it refutes is not evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .refute import ungrounded_quotes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify every memo quote is sourced.")
    ap.add_argument("--prose", required=True, help="path to the memo (brief.md)")
    ap.add_argument("--data", required=True, help="path to evidence.json from collection")
    ap.add_argument("--thesis", default="", help="the thesis, excluded from the check")
    a = ap.parse_args(argv)

    items = json.loads(Path(a.data).read_text()).get("items", [])
    prose = Path(a.prose).read_text()
    bad = ungrounded_quotes(prose, items, ignore=a.thesis)
    if bad:
        print(f"FAIL — {len(bad)} ungrounded quote(s) (not found in any source):", file=sys.stderr)
        for q in bad:
            print(f"  · {q}", file=sys.stderr)
        return 1
    print("OK — every quote is grounded in a collected source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
