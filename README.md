# Devil's Receipt

A **pre-decision red-team for your own theses**. State a position you hold; get
the strongest *evidenced* case against it, weighed against the case for, with a
verdict and the concrete triggers that would change your mind.

It fights the #1 decision failure — researching until you feel right. Built to be
used at a *moment*: before you size a trade, ship a call, commit to a view. A
devil's advocate that brings receipts (url, date, source tier, verbatim quote)
and stays honest (it weighs the bear case, never just stacks it).

Born from the de Bono *Distortion* provocation — "write the conclusion first,
then collect the evidence to break it" — but the output is calibrated, not
one-sided: a weak or empty bear case is a valid, honest result.

> Not OSINT. It searches news/social headlines, not entity records (registries,
> filings, WHOIS). It stress-tests a *claim*, it doesn't build a *dossier*.

## How it works

1. A thesis becomes two query sets — **disconfirming** (the work) and a few
   **confirming** (for the counterweight).
2. `devils-receipt` runs them through vendored **keyless** collectors (Google
   News, Reddit, Hacker News, GitHub), dedupes, tags each by source tier
   (`wire` / `unknown` / `junk` / `social` / `code`), and writes `evidence.json`.
3. The model writes a memo: bear case (tiered, cited, realized-vs-forward-risk) →
   *would change my mind* triggers → counterweight → **verdict**.
4. [`claimcheck`](https://github.com/FrancyJGLisboa/claimcheck) verifies dates are
   in-window and signs a tamper-evident receipt; a substring check confirms every
   quote is real.

No API keys. Runtime is stdlib-only — the collectors are vendored, not imported
from elsewhere.

## Run it on any agent surface

It's an agent skill, for people who use agent skills. Two collection paths — full
fidelity where there's a shell, model-native where there isn't.

| Surface | How | Collection | Integrity |
|---|---|---|---|
| **Claude Code** | drop `SKILL.md` in your skills dir; `pip install` below | keyless collectors | `claimcheck` receipt |
| **Copilot CLI** | install as a plugin skill (`SKILL.md`); same `pip install` | keyless collectors | `claimcheck` receipt |
| **Claude.ai** | add `SKILL.md` as a Project skill / instructions | model web search | model-checked |
| **ChatGPT** | paste `SKILL.md` body into a Custom GPT's instructions | browsing | model-checked |

Shell surfaces (Claude Code, Copilot CLI) — install from the public repo, no
local checkout needed:

```bash
pip install "devils-receipt[dev] @ git+https://github.com/FrancyJGLisboa/devils-receipt.git"
```

Chat surfaces (Claude.ai, ChatGPT) run Path B in `SKILL.md` — the model collects
with its own web search and labels the result *model-checked, not receipt-verified*.

## Develop

```bash
git clone https://github.com/FrancyJGLisboa/devils-receipt && cd devils-receipt
uv pip install -e ".[dev]"     # runtime + tests + claimcheck (integrity gate)
```

## Use

```bash
# 1. collect disconfirming evidence
python -m devils_receipt \
  --queries "safrinha corn drought damage;Brazil corn crop downgrade;Mato Grosso corn losses" \
  --from 2026-05-25 --to 2026-06-25 --out evidence.json

# 2. (model writes the memo brief.md citing the candidates) then:
claimcheck --prose brief.md --data evidence.json --window 2026-05-25,2026-06-25 --quotes
```

As a Claude Code skill, `SKILL.md` drives the full loop — symlink it into your
skills dir and invoke `/devils-receipt "the thesis you hold"`.

## The loss function

Deterministic checks in `evals/run_eval.py`: provenance (every quote is sourced),
no-fabrication (empty evidence ⇒ the memo cites nothing, but still verdicts),
receipt integrity (round-trips, tamper fails), date sanity (no stale citations).
Relevance and verdict calibration are judged live on the real memo.

```bash
uv run pytest          # unit tests for the dedup + provenance logic
uv run python evals/run_eval.py
```

## License

MIT
