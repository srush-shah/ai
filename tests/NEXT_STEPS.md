# Next Steps — Classifier Accuracy & Elderly Fix

Status: **investigation complete, overfitting check done, no production code changed.**
All findings are runnable. See `tests/RESULTS.md` for full benchmark details.

---

## TL;DR for leads discussion

### The honest numbers (fresh 36-case holdout, neither approach tuned against it)

| | LLM (Rahul's) | Embedding + boost (ours) |
|---|---|---|
| **Top-1** | **88.9%** | 80.6% |
| **Top-3** | **91.7%** | **91.7%** (tied) |
| Latency | 11.68s | 0.05s |
| LLM calls | ~3 / req | 0 |
| API cost | Yes | $0 |
| Deterministic | No | Yes |

LLM wins top-1 by ~8 points. Both approaches are tied on top-3. Embedding is
230× faster and free.

### What was overfitting

We originally reported 97.4% top-1 for embedding. That was inflated by a
confidence threshold (return GENERAL_CATEGORY when similarity < 0.40) that had
been calibrated to 2 specific queries in the original 77-case set. On fresh
phrasing the same threshold rejected dozens of legitimate requests. **The
threshold has been removed.** The clean post-improvement number on the original
set is 94.8%, and on fresh cases 80.6%.

### What is real

The routing improvements to `is_elderly_context()` and the category description
rewrites both survived the holdout check. The elderly section is now 21/21 on
the original set and passes on fresh elderly phrasings too.

---

## Decision to bring to leads

### 1. Which approach do we ship?

**Option A — Ship embedding + boost as primary path.**
- Pro: 230× faster, $0/request, deterministic, no rate-limit risk, top-3 tied with LLM.
- Con: Top-1 lags LLM by ~8 points on unseen data. Several phrasing variants
  (age numbers, ambiguous person words) still miss.
- Verdict: viable if top-3 is the product metric, or if latency/cost are hard constraints.

**Option B — Ship Rahul's improved LLM as primary path.**
- Pro: Better top-1 on unseen data (88.9%). Handles novel phrasings more
  naturally. No new model dependency.
- Con: ~12s latency, API cost, nondeterministic, rate-limit risk at scale.
- Verdict: viable if top-1 accuracy is the hard constraint.

**Option C — Embed first, LLM only when confidence is low (true hybrid).**
- Embedding handles ~80% of requests correctly at 0.05s / $0. Route the
  remaining low-confidence cases to the LLM. Net: most users get instant
  results; hard cases still get the LLM's accuracy.
- Requires: a calibrated confidence threshold — which needs more labeled data
  than the current 77/36-case sets to set reliably. Not ready now.
- Verdict: the right long-term architecture; not implementable today.

### 2. Deployment of the embedding model

`all-MiniLM-L6-v2` is ~90 MB. Three options for Lambda:

| Option | Cold start impact | Operational complexity |
|---|---|---|
| Lambda layer | Medium (~2–3s extra) | Low |
| EFS mount | Low (model persists across invocations) | Medium |
| Container image | None (baked in) | Higher (CI/CD change) |

Needs a sizing and cold-start spike before any deployment decision.

### 3. Rahul's SSM key loading

`utils/client.py` now loads API keys from SSM Parameter Store (with env-var
fallback for local dev). This is a needed improvement regardless of which
classifier wins — it should be merged.

---

## Open questions

1. **Is top-1 or top-3 the product metric?** If the UI surfaces 3 suggestions
   and users pick from them, top-3 (tied at 91.7%) is what matters. If only
   one category is shown, LLM's top-1 lead is significant.

2. **What does the real traffic distribution look like?** The 77+36 cases are
   author-written and may over-represent clean, clear requests. If production
   traffic is messier, LLM's robustness to novel phrasing may be even more
   valuable.

3. **Taxonomy review for intra-6.* confusion.** `6.8` SOCIAL_CONNECTION vs
   `6.1` SENIOR_RELOCATION and `6.5` ERRANDS vs `1.2` GROCERY_DELIVERY are
   structurally ambiguous — the task is nearly identical, distinguished only by
   who it's for. A small taxonomy change (e.g., a shared "elderly assistance"
   flag rather than mirrored leaf categories) might fix this more cleanly than
   any classifier tuning.

4. **Age-number routing.** Neither approach handles "I am 78 years old" as an
   elderly signal. `is_elderly_context()` works on keyword patterns; the LLM
   infers age context from semantics. If this pattern is common in real traffic,
   the embedding approach needs either an age-regex rule or a small age-detection
   model.

5. **GENERAL_CATEGORY handling.** Without a threshold, embedding always returns
   a leaf even for genuinely unclear requests. A reliable solution requires
   enough labeled ambiguous-request examples to set a threshold that doesn't
   over-fire on legitimate low-confidence requests. Not enough data yet.

---

## What's runnable today

| File | Purpose |
|---|---|
| `services/embedding_service.py` | Embedding approach with elderly boost/route. |
| `services/hybrid_service.py` | Embedding → 1 LLM call fallback. |
| `services/zero_shot_service.py` | Zero-shot NLI (benchmarked, rejected). |
| `services/classification_service.py` | LLM hierarchical approach (Rahul's). |
| `utils/routing_for_categories.py` | Improved `is_elderly_context()`. |
| `utils/categories_with_description.py` | Enriched category descriptions. |
| `tests/test_cases.py` | Original 77 labeled cases. |
| `tests/fresh_test_cases.py` | 36 fresh holdout cases (overfitting check). |
| `tests/evaluate.py` | Benchmark harness. Use `--fresh` for holdout set. |
| `tests/results/*.json` | Persisted run logs. |

Reproduce any number:
```bash
# Fresh holdout — the honest comparison
venv/bin/python tests/evaluate.py --fresh --approach emb_boost
venv/bin/python tests/evaluate.py --fresh --approach llm

# Original set (optimistic; used for development)
venv/bin/python tests/evaluate.py --approach emb_boost --failures
```

## Concrete integration plan (pending sign-off)

If **Option A** (embedding) is chosen:
1. Point `lambda_function.py` → `services.embedding_service.predict_categories(description, elderly_strategy="boost")`.
2. Resolve Lambda packaging question (Q2 above).
3. Add `sentence-transformers` to `requirements.txt`.
4. Confirm embeddings persist across warm Lambda invocations (already lazy-loaded in `_get_index()`).
5. Merge Rahul's SSM key loading regardless.
6. Expand labeled set from real traffic; re-run before cutover.

If **Option B** (LLM) is chosen:
1. Merge Rahul's `classification_service.py`, `category_similarity.py`, `routing_for_categories.py`, `client.py`.
2. Monitor latency and rate-limit headroom under real traffic.

If **Option C** (hybrid) is chosen:
1. Collect ~200+ labeled real-traffic examples to calibrate a confidence threshold safely.
2. Implement: embed → if top-1 similarity ≥ threshold, return; else call LLM.
3. A/B test threshold values before hardening.
