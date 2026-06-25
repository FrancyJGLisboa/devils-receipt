---
name: devils-receipt
description: >
  A pre-decision red-team for your own theses, portable across agent surfaces.
  State a position you hold; this builds the strongest evidenced case AGAINST it,
  weighs it against the case FOR, and gives a verdict with the triggers that
  would change your mind. Use when the user says "red-team this", "what am I
  missing", "stress-test my thesis", "make the bear case", "play devil's
  advocate", "before I commit to X", or invokes /devils-receipt. Works best on
  market / macro / domain theses where public reporting is the right source. Not
  OSINT (no entity dossiers) — decision hygiene for someone holding a view.
---

# Devil's Receipt

A devil's advocate that brings receipts. You hold a thesis; this hunts the
evidence that would break it, tiers the sources, weighs it against why you might
be right, and tells you whether to hold or fold — plus the concrete triggers to
watch. It fights the #1 decision failure: researching until you feel right.

Use it at a *moment* — before you commit to a view, size a trade, ship a call.

## Two ways to run it (pick by your surface)

**Path A — shell surfaces (Claude Code, Copilot CLI): full fidelity.**
Keyless Python collectors + `claimcheck` integrity receipt. Set up once:
```
pip install "devils-receipt[dev] @ git+https://github.com/FrancyJGLisboa/devils-receipt.git"
```
(The `[dev]` extra pulls `claimcheck`, the integrity gate.)

**Path B — chat surfaces (Claude.ai, ChatGPT): model-native.**
No local shell, so you can't run the collectors. Use *your own web search* to
collect, follow the same method below, and label the result
**"integrity: model-checked, not receipt-verified"** — quotes must be copied
verbatim with a working link, and you must not invent figures. (For full
receipts here, point a hosted collector endpoint at the chat tool — optional.)

## Procedure

1. **Read the thesis. Generate queries in two sets.**
   - **Disconfirming (the work):** 5–8 angles that would make the thesis false —
     failure / risk / downgrade / cut / delay framing + the named entities.
   - **Confirming (for the counterweight):** 2–3 angles that would support it.
     You need both to *weigh* the case, not just stack the bear side.

2. **Collect.**
   - *Path A:* `python -m devils_receipt --queries "q1;q2;q3;..." --from YYYY-MM-DD
     --to YYYY-MM-DD --out evidence.json` — prints candidates tagged
     `[source/tier]`.
   - *Path B:* run each query through your web-search tool; record title, url,
     date, publisher, and a verbatim snippet per hit.
   - **Tier every source:** `wire` (Reuters/Bloomberg/AP/established trade press),
     `unknown` (everything else), `social` (Reddit/forums/X). Weight by tier — a
     `wire` beats a `social` post; never lead the bear case with a `junk` or
     alarmist `social` item.

3. **Write the memo** (`brief.md`) in this exact shape:
   ```
   THESIS  <restated>
   BEAR CASE  <none | weak | moderate | strong> — <n realized, n forward-risk>

   ▸ <how it threatens the thesis>
       <publisher> · <date> · tier: <wire|social|…> · conf: <low|med|high>
       "<verbatim quote>"   — <url>
   ▸ …

   WOULD CHANGE MY MIND
     • <specific, checkable trigger>           (leading indicators, not vibes)
   COUNTERWEIGHT (why you may be right)
     <the confirming signals you found, named>
   VERDICT  <hold | trim | fold> — <one line>
   ```
   - Keep only threats that genuinely make the thesis false; drop keyword
     false-positives. Distinguish **realized** (already happened) from
     **forward-risk** (might) — never inflate the latter into the former.
   - **If the bear case is empty or weak, say so** — `BEAR CASE none/weak` with a
     `hold` verdict is a valid, honest result. Do NOT manufacture threats. Absence
     of a strong bear case is real signal.

4. **Verify (Path A only).**
   ```
   claimcheck --prose brief.md --data evidence.json --window FROM,TO --quotes
   python -c "import json,claimcheck.receipt as r; print(json.dumps(r.build_receipt(
     'evidence.json','brief.md',[{'level':'info','rule':'devils-receipt','term':'signed'}])))" > receipt.json
   ```
   Exit 0 = no stale-date errors; figure warnings advisory.

## Worked example

**Thesis:** *"Brazil's safrinha corn is fine this year."* Window: last 30 days.
After collecting disconfirming + confirming queries, the honest output was:

```
THESIS  Brazil's safrinha corn is fine this year
BEAR CASE  none — 0 realized, 0 forward-risk
  (only candidates were a price tick + a US-China export story — off-topic)
WOULD CHANGE MY MIND
  • CONAB revises the 2025-26 corn number DOWN in a later report
  • a wire-tier (not social) report of realized drought/frost damage
COUNTERWEIGHT (why you may be right — and it's strong)
  "Brazil Grain Harvest Record 358.6 Million Tonnes" (CONAB, wire) ·
  "USDA signals ample supplies" (Farm Progress) · prices falling on record harvest
VERDICT  hold — evidence weight is lopsided toward the thesis; abundance, not risk
```

The point: it refused to manufacture a bear case for a thesis the evidence
confirms, and said *why* you're probably right. That honesty is the product.

## Output to the user

The memo verbatim. Never soften the bear case to spare feelings, never inflate it
to seem thorough. The calibrated other-side is the value; the verdict is the
product.

## Success criteria (loss function)

Deterministic on Path A (`evals/run_eval.py`): provenance — every ≥4-word quote
appears in some collected item; no-fabrication — a weak/empty bear case still
verdicts, never invents threats; receipt round-trips, tamper fails; dates
in-window. Judged live (both paths): bear-case items genuinely threaten the
thesis, and the verdict matches the evidence weight.
