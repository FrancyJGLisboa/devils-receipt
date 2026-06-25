---
name: devils-receipt
description: >
  State a belief; this refuses to confirm it and hunts open sources that would
  prove you WRONG, each shown as a receipt (url + date + exact quote). Inverts
  the confirmation-bias search. Keyless. Use when the user says "prove me wrong",
  "what am I missing", "stress-test this belief", "red-team this claim", "devil's
  advocate", "find disconfirming evidence", or invokes /devils-receipt. NOT a
  balanced summary — it is one-sided by design, toward refutation.
---

# Devil's Receipt

Edward de Bono's **Distortion** operator made operational: write the conclusion
first, then collect only the evidence that breaks it. The point is to fight the
#1 amateur-OSINT failure — searching until you feel right.

You (Claude) do the part heuristics do badly: turn a belief into good refutation
angles and judge which results actually threaten it. The vendored keyless
collectors do I/O. `claimcheck` is the integrity gate.

> Setup once: `uv pip install -e "/Users/francylisboacharuto/devils-receipt[dev]"`
> (the `[dev]` extra pulls in `claimcheck`, the step-4 integrity gate).

## Procedure

1. **Read the belief. Generate 5–8 DISCONFIRMING queries** — negations, the
   failure/risk/downgrade/cut/delay framing, and the named entities. Search for
   what would make the belief false, never what confirms it.
   - "Brazil's safrinha corn is fine this year" →
     `safrinha corn drought damage; Mato Grosso corn losses; Brazil corn crop
     downgrade; CONAB corn cut; second corn frost risk; Brazil corn export delay`

2. **Collect** (window = last ~30 days unless the user gives one):
   ```
   python -m devils_receipt --queries "q1;q2;q3;q4;q5" \
     --from YYYY-MM-DD --to YYYY-MM-DD --out evidence.json
   ```
   Pulls candidates from Google News / Reddit / Hacker News / GitHub, dedupes,
   writes `evidence.json`, prints ranked candidates.

3. **Filter to genuine threats, write `brief.md`.** Keep only items that would
   actually make the belief *false* — discard keyword false-positives and
   anything that merely *supports* it (this brief is one-sided by design). For
   each kept item cite: the exact quoted snippet copied verbatim from the
   candidate's body (so it grounds), the url, and the date. Lead each bullet with
   *how it threatens the belief*.
   - **If nothing genuinely disconfirming survives**, do NOT pad. Emit exactly:
     > **No refutation found ≠ confirmed.** Open sources in this window surfaced
     > nothing that contradicts the belief. Absence of refutation is not evidence
     > the belief is true — only that the open web hasn't disputed it yet.

4. **Verify + sign:**
   ```
   claimcheck --prose brief.md --data evidence.json \
     --window YYYY-MM-DD,YYYY-MM-DD --quotes
   ```
   `--quotes` is required (the brief legitimately carries source quotes). Exit 0
   = no stale-date errors; figure warnings are advisory. Fix and re-run on error.
   Then sign a receipt (proves brief+evidence weren't altered):
   ```
   python -c "import json,claimcheck.receipt as r; \
     print(json.dumps(r.build_receipt('evidence.json','brief.md', \
     [{'level':'info','rule':'devils-receipt','term':'signed'}]), indent=2))" > receipt.json
   ```

## Output to the user

The `brief.md` content, then one line: *"N source(s) that threaten your belief;
verified, receipt signed."* — or the honest-null statement if nothing survived.
Never soften the belief or add reassurance. The job is the strongest available
case against what the user believes.

## Success criteria (the loss function)

Deterministic, checked by `evals/run_eval.py`:
- **Provenance** — every ≥4-word quote in the brief appears verbatim in some
  collected item (`refute.ungrounded_quotes` returns empty).
- **Honest-null** — empty evidence ⇒ brief contains the no-refutation marker.
- **Receipt integrity** — `claimcheck.verify_receipt` round-trips; tamper fails.
- **Date sanity** — `claimcheck` reports no `date-out-of-window` errors.

Judged live (semantic, needs your read of the brief):
- **Zero-confirmation** — no surfaced item supports the belief.
- **Relevance** — each item genuinely threatens the belief (≥70% true-threats).
