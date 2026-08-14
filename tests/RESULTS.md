# Classification Approach Comparison

Goal: improve endpoint accuracy and reduce reliance on per-request LLM calls.
We benchmarked approaches against two test sets:

- **Original set** — 77 hand-written cases covering every leaf category, with
  extra weight on elderly / healthcare / food boundary cases. Used for
  development and tuning. Numbers here should be treated as *upper bounds*.
- **Fresh holdout** — 36 cases written independently, without looking at the
  original set, specifically to check for overfitting. These are the honest
  numbers for a leads discussion.

Run it yourself:

```bash
venv/bin/python tests/evaluate.py                      # all approaches, original set
venv/bin/python tests/evaluate.py --fresh              # fresh holdout only
venv/bin/python tests/evaluate.py --fresh --failures   # with per-failure detail
venv/bin/python tests/evaluate.py --approach emb_boost --fresh
venv/bin/python tests/evaluate.py --log                # write JSON to tests/results/
```

## Metrics

- **Top-1 Acc** — exact leaf category is the #1 prediction (the production metric).
- **Top-3 Acc** — exact leaf category appears in the top 3 returned.
- **Parent Acc** — top-1 lands in the correct *parent* branch (right domain, wrong leaf).
- **Avg Latency** — wall-clock per request, CPU, cold caches warmed.

---

## Results on the fresh holdout (36 cases) — use these for decisions

These cases were written blind to the original test set. Neither routing logic
nor descriptions were tuned against them.

| Approach                     | Top-1   | Top-3   | Parent  | Latency | LLM calls |
|------------------------------|---------|---------|---------|---------|-----------|
| **LLM baseline (Rahul's)**   | **88.9%** | 91.7%  | 91.7%   | 11.68s  | ~3 / req  |
| Embedding + elderly boost    | 80.6%   | **91.7%** | 88.9% | 0.05s   | 0         |

**Top-3 is tied.** LLM leads top-1 by ~8 points; embedding matches it on top-3
and is 230× faster with zero API cost.

---

## Results on the original 77-case set — context only

Included for completeness. Because routing and descriptions were iteratively
tuned while looking at these failures, the numbers are optimistic.

| Approach                       | Top-1    | Top-3   | Parent  | Latency  | LLM calls |
|--------------------------------|----------|---------|---------|----------|-----------|
| Embedding + elderly boost¹     | **94.8%** | **96.1%** | **96.1%** | 0.05s | 0      |
| LLM baseline (Rahul's)         | 92.2%    | 93.5%   | 93.5%   | 12.93s   | ~3 / req  |
| Hybrid (emb → 1 LLM)           | 88.3%    | 94.8%   | 90.9%   | 4.02s    | 1 / req   |
| Embedding similarity (no fix)  | 88.3%    | 93.5%   | 92.2%   | 0.05s    | 0         |
| Zero-shot NLI                  | 63.6%    | 79.2%   | 72.7%   | 1.54s    | 0         |

¹ After routing improvements described below. The "LLM baseline" row reflects
Rahul's improvements (`category_similarity.py` keyword pre-ranking +
`_predict_ranked_level` + SSM key loading), not the original LLM path.

---

## What the overfitting check revealed

A confidence threshold (≥ 0.40 → return GENERAL_CATEGORY) was trialled during
development. It looked good on the original set (97.4% top-1) but collapsed to
44.4% on fresh cases — **it had been calibrated to 7 specific queries in the
original set**. The threshold has been removed; GENERAL_CATEGORY handling
requires more labeled data before it can be implemented robustly.

---

## What genuinely improved (survives the holdout check)

### Routing improvements to `is_elderly_context()` (`utils/routing_for_categories.py`)

Three principled changes, verified on both sets:

1. **FP check runs before direct triggers.** Previously, the false-positive list
   was checked *after* direct triggers fired — meaning "senior software engineer"
   could still fire if "senior" were a direct trigger. Now the FP list is the
   first gate.

2. **`"senior"` moved to `ELDERLY_PERSON_TRIGGERS`.** Added as a person trigger
   (requires a context cue to fire) rather than a direct trigger. This means
   "I'm a senior and I need meals delivered" fires correctly (person trigger +
   "meals delivered" cue), while "I'm a senior student applying for internships"
   does not (no elderly context cue).

3. **Meal delivery cues added.** "meals delivered", "meal delivered", "food
   delivered", "meals to me" added to `ELDERLY_CONTEXT_CUES` so age-adjacent
   phrasing around meal delivery routes correctly into the elderly branch.

### Category description enrichment (`utils/categories_with_description.py`)

Descriptions were rewritten from instructional ("Use for X. Do not use for Y.")
to retrieval-friendly prose. The sentence-transformer model embeds query-style
text better than classification-rule style text. Changes that generalise:

| Category | Before | After (abbreviated) |
|---|---|---|
| `6.5` ERRANDS | "Assistance with errands or transport to events." | "Help running errands for an elderly or senior person — grocery pickup, pharmacy runs…" |
| `6.6` TRANSPORTATION | "Transport to appointments, events, or other destinations." | "Arranging a volunteer to drive or give a ride to a senior or elderly person…" |
| `6.8` SOCIAL_CONNECTION | "Companionship and social activities (calls, walks, games)." | "Companionship visits, friendly check-ins, or social activities for lonely or isolated seniors…" |
| `6.3` MEDICATION_MANAGEMENT | "Medication reminders or help organizing medications (non-clinical)." | "Help organizing or managing medications for an elderly or senior family member…" |
| `GARDEN` | "Garden maintenance, landscaping, and outdoor upkeep." | "Help with garden, lawn, and yard work — mowing the lawn, trimming plants, weeding…" |
| `MENTAL_WELLBEING_SUPPORT` | Long instructional text with "Do not use…" | "Feeling anxious, depressed, stressed, overwhelmed, or lonely and needing someone to talk to…" |
| `WOMENS_OR_REPRODUCTIVE_HEALTH` | "Women's health and reproductive health guidance." | "Women's health support including gynecologist consultations, routine checkups…" |
| `CAREER_GUIDANCE` | "Use for career advice… Do not use for health advice…" | "Resume review and feedback, preparing for job interviews, career advice, job search help…" |
| `HEALTH_EDUCATION_GUIDANCE` | Long instructional text | "General wellness education and healthy living tips — sleep habits, sleep hygiene…" |

---

## Remaining failure patterns (both approaches)

### Embedding + boost (fresh holdout, 7/36 failures)

| Case | Expected | Got | Notes |
|---|---|---|---|
| Navratri dinner for 40 | 1.3.2 FESTIVE_BULK_COOKING | 1.3.4 CULTURAL_CUISINE | In top-3; taxonomy boundary |
| Biryani recipe guidance | 1.3.4 CULTURAL_CUISINE | 1.1 FOOD_ASSISTANCE | Low confidence; phrasing mismatch |
| Parents + movers | 3.8 BOOKING_MOVERS | 6.1 SENIOR_RELOCATION | 6.1 description mentions "moving process" — false pull |
| Software engineering interview | 4.6 CAREER_GUIDANCE | 4.1 COLLEGE_APP | "applying" word matches 4.1 |
| 78 years old, meals | 6.9 MEAL_SUPPORT | 1.3.5 OTHER_COOKING | Age numbers don't trigger `is_elderly_context()` |
| Elderly woman, isolated, visitor | 6.8 SOCIAL_CONNECTION | 6.1 SENIOR_RELOCATION | Intra-branch 6.* confusion persists |
| Genuinely unclear request | 0.0.0.0.0 GENERAL_CATEGORY | 1.1 FOOD_ASSISTANCE | No threshold; embedding always returns a leaf |

### LLM baseline (fresh holdout, 4/36 failures)

| Case | Expected | Got | Notes |
|---|---|---|---|
| Eviction notice, paid on time | 3.2 TENANT_RENT | 3.1 LEASE_SUPPORT | In top-3; genuine taxonomy boundary |
| Software engineering interview | 4.6 CAREER_GUIDANCE | 4.3.4 COMPUTER_SCIENCE | "software engineering" pulls toward CS tutoring |
| Grandfather, 7 medications, mixing up | 6.3 MEDICATION_MGMT | 5.4 MEDICATION_REMINDERS | Persistent 6.3/5.4 ambiguity |
| Senior student, data science internship | 4.6 CAREER_GUIDANCE | 4.3.4 COMPUTER_SCIENCE | "data science" pulls toward CS tutoring |

---

## Elderly category — root-cause analysis

The core problem is **structural**: several elderly leaf categories describe the
same task as a non-elderly leaf, distinguished only by *who* the request is for.

| Elderly leaf | Collides with |
|---|---|
| `6.9` MEAL_SUPPORT | `1.2` GROCERY / `1.3.1` MEAL_PREP |
| `6.3` MEDICATION_MANAGEMENT | `5.4` MEDICATION_REMINDERS |
| `6.5` ERRANDS | `1.2` GROCERY_SHOPPING_AND_DELIVERY |
| `6.6` TRANSPORTATION | `5.x` medical-appointment intents |
| `6.8` SOCIAL_CONNECTION | No direct collision — but semantically close to `6.1` SENIOR_RELOCATION |

Both approaches handle most of these correctly **when the description contains an
explicit elderly keyword**. Both struggle when the only elderly signal is an age
number ("I am 78 years old") or an ambiguous person word ("my parents") without
a strong context cue.
