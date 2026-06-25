# Devil's Receipt

State a belief. Get back only the open-source evidence that would prove it
**wrong** — each finding a receipt with url, date, and the exact quote.

It refuses to confirm. The default failure of amateur OSINT is searching until
you feel right; Devil's Receipt inverts the search so the output is always *"here
is what threatens your belief"*, and silence is reported honestly as **"no
refutation found ≠ confirmed."** It is one-sided by design — a steel-manned case
*against* what you believe, not a balanced summary.

This is the de Bono *Distortion* provocation ("write the conclusion first, then
collect the evidence to break it") turned into a tool.

## How it works

1. A belief becomes 5–8 **disconfirming** queries (the model's job — failure/
   risk/downgrade framing + the named entities).
2. `devils-receipt` runs them through vendored **keyless** collectors (Google
   News, Reddit, Hacker News, GitHub), dedupes, and writes `evidence.json`.
3. The model keeps only items that genuinely make the belief false and writes a
   brief citing each verbatim.
4. [`claimcheck`](https://github.com/) verifies dates are in-window and signs a
   tamper-evident receipt; a substring check confirms every quote is real.

No API keys. Runtime is stdlib-only — the collectors are vendored, not imported
from elsewhere.

## Install

```bash
uv pip install -e .            # runtime (stdlib-only, keyless)
uv pip install -e ".[dev]"     # + tests + claimcheck (integrity gate, from GitHub)
```

## Use

```bash
# 1. collect disconfirming evidence
python -m devils_receipt \
  --queries "safrinha corn drought damage;Brazil corn crop downgrade;Mato Grosso corn losses" \
  --from 2026-05-25 --to 2026-06-25 --out evidence.json

# 2. (model writes brief.md citing the candidates) then:
claimcheck --prose brief.md --data evidence.json --window 2026-05-25,2026-06-25 --quotes
```

As a Claude Code skill, `SKILL.md` drives the full loop — symlink it into your
skills dir and invoke `/devils-receipt "your belief"`.

## The loss function

Deterministic checks in `evals/run_eval.py`: provenance (every quote is sourced),
honest-null (empty evidence ⇒ the marker), receipt integrity (round-trips, tamper
fails), date sanity (no stale citations). Zero-confirmation and relevance are
judged live on the real brief.

```bash
uv run pytest          # unit tests for the dedup + provenance logic
uv run python evals/run_eval.py
```

## License

MIT
