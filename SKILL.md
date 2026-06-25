---
name: devils-receipt
description: >
  A pre-decision red-team for your own theses. State a position you hold; this
  builds the strongest evidenced case AGAINST it, weighs it against the case
  FOR, and gives a verdict with the triggers that would change your mind. Use
  when the user says "red-team this", "what am I missing", "stress-test my
  thesis", "make the bear case", "play devil's advocate", "before I commit to
  X", or invokes /devils-receipt. The bear case is researched and cited; the
  counterweight and verdict keep it honest. Not OSINT (no entity dossiers) —
  decision hygiene for someone holding a position.
---

# Devil's Receipt

A devil's advocate that brings receipts. You hold a thesis; this hunts the
evidence that would break it, tiers the sources, weighs it against why you might
be right, and tells you whether to hold or fold — plus the concrete triggers to
watch. The point is to fight the #1 decision failure: researching until you feel
right.

Use it at a *moment* — before you commit to a position, size a trade, ship a
call. It is not a standing monitor and not entity intelligence.

> Setup once: `uv pip install -e "/Users/francylisboacharuto/devils-receipt[dev]"`
> (the `[dev]` extra pulls in `claimcheck`, the integrity gate).

## Procedure

1. **Read the thesis. Generate queries in two sets.**
   - **Disconfirming (the work):** 5–8 angles that would make the thesis false —
     failure / risk / downgrade / cut / delay framing + the named entities.
   - **Confirming (for the counterweight):** 2–3 angles that would support it.
     You need both to weigh the case, not just stack the bear side.
   - Thesis "Brazil's safrinha corn is fine this year" →
     disconfirm: `safrinha corn drought damage; CONAB corn cut; Mato Grosso corn
     losses; second corn frost risk` · confirm: `Brazil corn record harvest;
     Brazil corn supply ample`

2. **Collect** (window = last ~30 days unless given):
   ```
   python -m devils_receipt --queries "q1;q2;q3;..." \
     --from YYYY-MM-DD --to YYYY-MM-DD --out evidence.json
   ```
   Prints candidates tagged `[source/tier]` — tier is `wire` (reputable),
   `unknown`, `junk`, `social` (Reddit/HN), or `code` (GitHub). **Weight by tier:
   a `wire` beats a `social` post; never lead the bear case with a `junk` or
   alarmist `social` item.**

3. **Write the memo** (`brief.md`) in this exact shape:
   ```
   THESIS  <restated>
   BEAR CASE  <none | weak | moderate | strong> — <n realized, n forward-risk>

   ▸ <how it threatens the thesis>
       <publisher> · <date> · tier: <wire|social|…> · conf: <low|med|high>
       "<verbatim quote copied from the candidate body>"   — <url>
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
   - **If the bear case is empty or weak, say so** — `BEAR CASE  none/weak` with a
     `hold` verdict is a valid, honest result. Do NOT manufacture threats to fill
     the section. Absence of a strong bear case is real signal.

4. **Verify + sign:**
   ```
   claimcheck --prose brief.md --data evidence.json \
     --window YYYY-MM-DD,YYYY-MM-DD --quotes
   python -c "import json,claimcheck.receipt as r; \
     print(json.dumps(r.build_receipt('evidence.json','brief.md', \
     [{'level':'info','rule':'devils-receipt','term':'signed'}]), indent=2))" > receipt.json
   ```
   `--quotes` required. Exit 0 = no stale-date errors; figure warnings advisory.

## Output to the user

The memo verbatim. Never soften the bear case to spare feelings, and never
inflate it to seem thorough — the value is a calibrated other-side, not a
hatchet job. The honest verdict is the product.

## Success criteria (the loss function)

Deterministic (`evals/run_eval.py`): provenance — every ≥4-word quote appears in
some collected item; no-fabrication — a weak/empty bear case still yields a
verdict, never invented threats; receipt round-trips, tamper fails; dates
in-window. Judged live: bear-case items genuinely threaten the thesis (relevance),
and the verdict matches the evidence weight (calibration).
