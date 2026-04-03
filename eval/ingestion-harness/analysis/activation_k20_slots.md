# Activation Signal: How Many k20 Slots Does It Control?

**After 15 papers — 24-note corpus**

## The short answer

Right now: **~0 slots at the k=20 boundary.** At scale (~60–100 notes): **2–4 slots**.

## Current state (24 notes, k=20)

With 24 notes and k=20, only 4 notes are excluded per query. The activation gap at
the boundary (between 20th and 21st note by activation rank) is just **0.0038** — only
0.8% of the embedding signal range (weight 0.45). Any topically relevant note easily
overcomes this. Activation is not currently controlling *which* notes enter the cluster.

## What activation IS doing: hub over-sorting

The weight distribution after 15 papers is heavily concentrated:

| Note | Act. Weight | Norm. Score | Fusion Contribution |
|------|-------------|-------------|---------------------|
| z20260322-002 | 141.4 | 1.000 | 0.180 |
| z20260322-001 | 130.6 | 0.923 | 0.166 |
| z20260322-003 | 119.5 | 0.845 | 0.152 |
| z20260322-018 |  62.0 | 0.438 | 0.079 |
| z20260322-006 |  50.8 | 0.359 | 0.065 |
| ... | ... | ... | ... |
| z20260322-011 |  10.0 | 0.071 | 0.013 | ← 20th |
| z20260323-005 |   7.0 | 0.049 | 0.009 | ← 21st |
| z20260323-003 |   5.0 | 0.035 | 0.006 |
| z20260322-017 |   5.0 | 0.035 | 0.006 |
| z20260323-004 |   4.0 | 0.028 | 0.005 |

Top-3 hubs hold **46.5%** of all activation weight. Their fusion scores
(0.152–0.180) are 8–14x higher than notes at positions 16–20 (0.013–0.020).

**Effect:** the hub trio sort to the top of every retrieved cluster regardless of
topic relevance. L1 sees them first, with full body text. This is a sorting bias, not
a selection bias.

The three hubs are currently in the cluster on **embedding merit** — they're genuinely
central notes. Activation reinforces rather than distorts their presence right now.

## The scale threshold: ~60–100 notes

The max activation differential between a top hub and a low-activation note is
**0.175** — that's 39% of the embedding signal range. Once the corpus grows large
enough that k=20 is a real filter, a hub with 0.175 activation advantage will
displace genuinely relevant but low-activation notes. Estimated: **2–4 slots**
effectively controlled by activation at scale.

At that point, 3 hub slots would be ~75–100% of the activation budget — unacceptable
if those notes don't happen to be topically relevant to the current query.

## Tuning target for periodic global decay

A periodic global decay (multiply all activation weights by λ every x ingestions)
should keep the top-3 concentration below **~25% of total weight**. That's roughly
twice the "fair share" for 3 notes in a 24-note corpus (3/24 ≈ 12.5%), allowing
meaningful hub status without monopolising the signal.

Current state: top-3 = 46.5% of total weight.
Target: top-3 ≤ 25%.

Rough calibration: applying λ=0.85 every 5 ingestions over the 15-paper run would
have yielded approximately 27% — close to target. This is a starting point for
simulation, not a validated recommendation.

**What "good" looks like for tuning:** a hub note should appear in the retrieved
cluster for queries in its domain without appearing for queries clearly outside it.
At 24 notes this is not yet testable; at 100+ notes, held-out domain-crossing queries
would reveal hub pollution.

## Open question

The activation signal controls *k* slots proportional to `activation_weight / 0.18`
relative to the embedding+bm25 gap at the boundary. This is query-dependent and
becomes meaningful only when the corpus is large enough for the boundary to be
competitive. Simulation with λ tuning is best deferred until the 20-paper run is
complete and the corpus stabilises.

## Next step: validating decay parameters

The log history contains everything needed to simulate alternative decay schedules
(all co-activation events with timestamps/ingestion order). But simulation requires
a tuning target — and the 25% concentration heuristic above is not sufficient on its
own.

**Proposed validation approach (after 20-paper run):**

1. Let the 20-paper run complete and the corpus stabilise.
2. Select 20–30 held-out queries from **outside** this paper set — ideally spanning
   different domains to create cross-domain retrieval scenarios.
3. Run retrieval under three conditions:
   - Baseline: no decay (current behaviour)
   - Decay A: λ=0.85 every 5 ingestions
   - Decay B: λ=0.70 every 10 ingestions
4. For each condition, check: do the retrieved clusters for domain-crossing queries
   include fewer hub notes (reduced pollution), while clusters for in-domain queries
   retain relevant hubs (signal preserved)?
5. Use that measurement to tune λ and x — not the concentration ratio alone.

**What "good" looks like:** a hub note appears in the cluster for queries in its
domain; it does not appear for queries clearly outside it. Hub pollution is the
failure mode to measure, not hub presence per se.
