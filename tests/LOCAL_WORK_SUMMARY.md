# Local Work Summary — Classifier Accuracy Investigation

Everything in this document was done **on this machine**, on top of `predict-endpoint-v2`
(which is currently identical, commit-for-commit, to the local `embedding-rollback`
branch — the two diverge only in uncommitted working-tree state, described below).
**None of it has been committed or pushed.** `git status` on `predict-endpoint-v2`
shows it all as modified/untracked files.

Goal: reduce reliance on per-request LLM calls for the `/predict` category
classification endpoint, and fix known elderly-category misclassification.

---

## 1. What exists on disk right now

### Modified (tracked) files
| File | Change |
|---|---|
| `utils/client.py` | Added env-var fallback (`GROQ_API_KEY`/`GEMINI_API_KEY`) for when SSM Parameter Store lookup returns nothing — needed for local dev without SSM access. |
| `utils/routing_for_categories.py` | Three fixes to `is_elderly_context()` — see §3. |
| `utils/categories_with_description.py` | Rewrote ~9 category descriptions from instructional style to retrieval-friendly prose — see §3. |
| `.gitignore` | Ignore `tests/results/` (per-run JSON dumps) while keeping `tests/RESULTS.md` tracked. |

### New (untracked) files
| File | Purpose |
|---|---|
| `services/embedding_service.py` | New classification approach: sentence-transformer cosine similarity, no LLM. |
| `services/hybrid_service.py` | New approach: embedding retrieval (top 10) → 1 LLM call to rank. |
| `services/zero_shot_service.py` | New approach: zero-shot NLI cross-encoder. Benchmarked and rejected. |
| `tests/test_cases.py` | 77 hand-written labeled cases spanning every leaf category, weighted toward elderly/healthcare/food boundaries. |
| `tests/fresh_test_cases.py` | 36 cases written *independently*, blind to the original set, as an overfitting check. |
| `tests/evaluate.py` | Benchmark harness — runs any/all approaches against either test set, reports top-1/top-3/parent accuracy, latency, LLM-call count. |
| `tests/RESULTS.md` | Full benchmark write-up (kept up to date as the source of truth). |
| `tests/NEXT_STEPS.md` | Leads-facing decision doc — options, trade-offs, open questions. |
| `tests/results/` | JSON logs from individual `evaluate.py --log` runs. |

Existing, unmodified: `services/classification_service.py` (the current production
LLM-hierarchical approach, referred to below as "LLM baseline" / "Rahul's").
**`lambda_function.py` was never touched** — none of this is wired into the live
endpoint.

### The two local variants being compared
- **`predict-endpoint-v2`** (current checkout) — has the routing/description
  improvements from §3 applied.
- **`embedding-rollback`** — checked out in parallel via `git worktree` at
  `.worktrees/embedding-rollback/`. Same commits, but its working tree has the
  *original* (pre-improvement) `routing_for_categories.py` and
  `categories_with_description.py`. It exists purely as a controlled "before"
  baseline so the two layers of change (routing vs. descriptions) could be
  isolated and each one's contribution measured independently. It does **not**
  represent an older/different commit — it's a snapshot for A/B comparison.

---

## 2. Approaches built and benchmarked

Four classification approaches were implemented and run through `tests/evaluate.py`
against both test sets:

1. **Embedding similarity** (`embedding_service.py`) — precompute a sentence-transformer
   (`all-MiniLM-L6-v2`) embedding for every leaf category's name+description, embed
   the incoming request, rank by cosine similarity. Zero LLM calls, ~0.05s/request.
   Supports two elderly-handling strategies:
   - `boost`: when `is_elderly_context()` fires, add a flat `+0.15` (`ELDERLY_BOOST`)
     to every `6.*` (elderly) leaf's similarity before ranking.
   - `route`: when triggered, restrict candidates to `6.*` leaves only.
2. **Zero-shot NLI** (`zero_shot_service.py`) — `valhalla/distilbart-mnli-12-1`
   cross-encoder scoring (description, category-label) pairs as textual entailment.
   No training data needed. **Rejected** — far lower accuracy (61–64% top-1) and
   slower (~1.5s) than embeddings.
3. **Hybrid** (`hybrid_service.py`) — embed and retrieve top-10 candidate leaves,
   then one LLM call (Groq primary, Gemini fallback) to rank/pick among just those
   10. Cuts LLM calls from ~3/request (current hierarchical drill-down) to 1.
4. **LLM baseline** (`classification_service.py`, unmodified) — the current
   production hierarchical top-level→drill-down approach using Groq/Gemini.

All four expose the same interface: `predict_categories(description, top_k=3) -> (results, token_usage)`.

### How it was run
```bash
venv/bin/python tests/evaluate.py                        # all approaches, original 77-case set
venv/bin/python tests/evaluate.py --fresh                 # all approaches, fresh 36-case holdout
venv/bin/python tests/evaluate.py --approach emb_boost --fresh --failures
venv/bin/python tests/evaluate.py --log                   # persist JSON to tests/results/
```
(`venv/` pins Python 3.11.14 locally; the shell default was 3.14, which the
dependencies here don't support.)

---

## 3. The two layers of improvement tested (isolated via the rollback worktree)

### Layer A — `is_elderly_context()` routing (`utils/routing_for_categories.py`)
Three fixes, each verified against both test sets:
1. **False-positive check moved before direct triggers.** Previously a direct
   trigger word could fire even when an FP phrase should have excluded it (e.g.
   "senior software engineer" being caught if "senior" were a direct trigger).
2. **`"senior"` reclassified as a person trigger, not a direct trigger** — now
   requires an accompanying context cue to fire. "I'm a senior and need meals
   delivered" fires; "I'm a senior student applying for internships" does not.
3. **Added meal-delivery context cues** — "meals delivered", "meal delivered",
   "food delivered", "meals to me" — so age-adjacent phrasing routes correctly.

### Layer B — category description rewrites (`utils/categories_with_description.py`)
~9 descriptions rewritten from instructional/rule style ("Use for X. Do not use
for Y.") to retrieval-friendly prose, since the sentence-transformer embeds
query-style text better than classification-rule text. Touched: `GARDEN`,
`CAREER_GUIDANCE`, `WOMENS_OR_REPRODUCTIVE_HEALTH`, `MENTAL_WELLBEING_SUPPORT`,
`HEALTH_EDUCATION_GUIDANCE`, `MEDICATION_MANAGEMENT`, `ERRANDS_EVENTS_TRANSPORTATION`,
`TRANSPORTATION_APPOINTMENTS_EVENTS`, `SOCIAL_CONNECTION` (full before/after table
in `tests/RESULTS.md`).

### What isolating the two layers showed (fresh 36-case holdout)
| Layer | Top-1 impact | Top-3 impact |
|---|---|---|
| A — routing | none (80.6% either way) | none |
| B — descriptions | none (80.6% either way) | **+5.6 pts** (86.1% → 91.7%) |

Routing fixes corrected real logic bugs but didn't move accuracy on fresh data
because those specific cases were already handled correctly by embedding
similarity regardless. Description rewrites are the change that measurably
generalizes.

---

## 4. Benchmark results

### Fresh 36-case holdout (the honest numbers — cases never seen during tuning)
| Approach | Top-1 | Top-3 | Parent | Latency | LLM calls |
|---|---|---|---|---|---|
| LLM baseline | **88.9%** | 91.7% | 91.7% | 11.68s | ~3/req |
| Embedding + boost (current, both layers applied) | 80.6% | **91.7%** | 88.9% | 0.05s | 0 |
| Embedding + boost (rollback, original routing/descriptions) | 80.6% | 86.1% | 88.9% | 0.05s | 0 |

LLM leads top-1 by ~8 points; embedding ties top-3 and is ~230× faster at $0/request.

### Original 77-case set (used for development; optimistic — routing/descriptions were tuned against it)
| Approach | Top-1 | Top-3 | Parent | Latency | LLM calls |
|---|---|---|---|---|---|
| Embedding + elderly boost | **94.8%** | **96.1%** | **96.1%** | 0.05s | 0 |
| LLM baseline | 92.2% | 93.5% | 93.5% | 12.93s | ~3/req |
| Hybrid (emb → 1 LLM) | 88.3% | 94.8% | 90.9% | 4.02s | 1/req |
| Embedding similarity (no elderly fix) | 88.3% | 93.5% | 92.2% | 0.05s | 0 |
| Zero-shot NLI | 63.6% | 79.2% | 72.7% | 1.54s | 0 |

### A confidence threshold that didn't survive scrutiny
Early in the investigation, a similarity threshold (≥0.40 → return
`GENERAL_CATEGORY`) was trialled and looked great — 97.4% top-1 on the original
set. On the fresh holdout it collapsed to 44.4%: it had been calibrated to 2
specific queries in the 77-case set. **It was removed.** This is why the
"clean" embedding numbers above (94.8% original / 80.6% fresh) are lower than
that early figure — the early number was an overfitting artifact.

---

## 5. Root cause: elderly-category structural collisions
Several `6.*` (elderly) leaves describe the *same task* as a non-elderly leaf,
differing only in who the request is for:

| Elderly leaf | Collides with |
|---|---|
| `6.9` MEAL_SUPPORT | `1.2` GROCERY / `1.3.1` MEAL_PREP |
| `6.3` MEDICATION_MANAGEMENT | `5.4` MEDICATION_REMINDERS |
| `6.5` ERRANDS | `1.2` GROCERY_SHOPPING_AND_DELIVERY |
| `6.6` TRANSPORTATION | `5.x` medical-appointment intents |
| `6.8` SOCIAL_CONNECTION | no direct collision, but semantically close to `6.1` SENIOR_RELOCATION |

Both the embedding and LLM approaches handle these correctly when an explicit
elderly keyword is present, and both struggle when the only elderly signal is
an age number ("I am 78 years old") or an ambiguous person word ("my parents")
without a strong context cue. Production currently hides this behind the
keyword-based `is_elderly_context()` shortcut rather than resolving it at the
taxonomy level.

---

## 6. Remaining failure patterns (fresh holdout)

**Embedding + boost, 7/36 failures** — mostly taxonomy boundary calls (e.g.
Navratri dinner → correct answer in top-3 but not top-1), one false pull from
overlapping description wording (`6.1` SENIOR_RELOCATION mentions "moving
process", pulling in a movers request), and no-threshold behavior always
returning a leaf even for genuinely unclear requests.

**LLM baseline, 4/36 failures** — genuine taxonomy boundary cases (e.g.
eviction vs. rent) and a persistent `6.3`/`5.4` medication ambiguity.

Full per-case tables are in `tests/RESULTS.md`.

---

## 7. Status and what's not decided yet

**Nothing has shipped.** `lambda_function.py` is untouched; production still
runs the unmodified LLM hierarchical path. This was explicitly paused for a
leads discussion before any integration decision. Open questions captured in
`tests/NEXT_STEPS.md`:

1. Is top-1 or top-3 the actual product metric? (They tie on top-3; LLM leads
   top-1 by ~8 points.)
2. Does the 77+36 hand-written case distribution reflect real traffic, or does
   real traffic skew messier (favoring the LLM's robustness)?
3. Should the taxonomy itself change (e.g. a shared "elderly assistance" flag
   instead of mirrored `6.*` leaves) rather than tuning classifiers around the
   collision?
4. Age-number elderly detection ("I am 78 years old") isn't handled by either
   approach's current routing.
5. `GENERAL_CATEGORY` / low-confidence handling needs more labeled data before
   a threshold can be set without overfitting again.
6. Lambda packaging of the ~90MB `all-MiniLM-L6-v2` model (layer vs. EFS mount
   vs. container image) needs a cold-start spike before any deployment decision.

Three options are on the table (detailed with pros/cons in `tests/NEXT_STEPS.md`):
**(A)** ship embedding+boost as primary, **(B)** ship the current LLM path as-is
(its SSM key-loading fix should merge regardless of which wins), **(C)** true
hybrid — embed first, fall back to LLM only on low confidence — flagged as the
right long-term architecture but not implementable yet for lack of a
calibration dataset.
