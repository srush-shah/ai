"""
Evaluation harness: runs all classification approaches on the test set
and logs accuracy, top-3 hit rate, and latency side-by-side.

Usage:
    python3 tests/evaluate.py                  # all approaches
    python3 tests/evaluate.py --approach emb   # embedding only
    python3 tests/evaluate.py --approach zs    # zero-shot NLI only
    python3 tests/evaluate.py --approach hybrid
    python3 tests/evaluate.py --approach llm   # current baseline
    python3 tests/evaluate.py --elderly        # only elderly boundary cases
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_cases import TEST_CASES
from utils.categories import help_categories


def _resolve(key: str):
    """Lazily build the predict_categories callable for an approach key.

    Lazy imports keep heavy deps (torch) out of LLM-only runs.
    """
    if key == "emb":
        from services.embedding_service import predict_categories
        return predict_categories
    if key == "emb_boost":
        from services.embedding_service import predict_categories
        return lambda d: predict_categories(d, elderly_strategy="boost")
    if key == "emb_route":
        from services.embedding_service import predict_categories
        return lambda d: predict_categories(d, elderly_strategy="route")
    if key == "zs":
        from services.zero_shot_service import predict_categories
        return predict_categories
    if key == "hybrid":
        from services.hybrid_service import predict_categories
        return predict_categories
    if key == "llm":
        from services.classification_service import predict_categories
        return predict_categories
    raise ValueError(f"unknown approach: {key}")


APPROACH_MAP = {
    "emb":       ("Embedding similarity",      _resolve),
    "emb_boost": ("Embedding + elderly boost", _resolve),
    "emb_route": ("Embedding + elderly route", _resolve),
    "zs":        ("Zero-shot NLI",             _resolve),
    "hybrid":    ("Hybrid (emb + LLM)",        _resolve),
    "llm":       ("LLM baseline",              _resolve),
}

ELDERLY_BOUNDARY_NOTES = {
    "medication reminders, no elderly context",
    "general checkup, no elderly",
    "health education, no elderly",
    "weak trigger + cue -> elderly transport",
    "weak trigger + medication -> elderly",
    "medication reminders - no elderly trigger",
}


def _get_parent(cat_id: str) -> str:
    parts = cat_id.split(".")
    if len(parts) <= 1:
        return cat_id
    return ".".join(parts[:-1])


def _top1_correct(pred: list[dict], expected_id: str) -> bool:
    if not pred:
        return False
    return pred[0]["category_number"] == expected_id


def _top3_correct(pred: list[dict], expected_id: str) -> bool:
    return any(r["category_number"] == expected_id for r in pred)


def _parent_correct(pred: list[dict], expected_id: str) -> bool:
    """Top-1 prediction lands in the right parent (sub-category off but domain correct)."""
    if not pred:
        return False
    return _get_parent(pred[0]["category_number"]) == _get_parent(expected_id)


def evaluate_approach(key: str, label: str, cases: list) -> dict:
    predict_fn = _resolve(key)

    results = []
    latencies = []

    for description, expected_id, notes in cases:
        t0 = time.perf_counter()
        try:
            predictions, _ = predict_fn(description)
        except Exception as e:
            print(f"  ERROR on '{description[:50]}': {e}")
            predictions = []
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)

        top1 = _top1_correct(predictions, expected_id)
        top3 = _top3_correct(predictions, expected_id)
        parent = _parent_correct(predictions, expected_id)

        predicted_id = predictions[0]["category_number"] if predictions else "—"
        predicted_name = help_categories.get(predicted_id, "—")
        expected_name = help_categories.get(expected_id, "—")

        results.append({
            "description": description,
            "expected": expected_id,
            "expected_name": expected_name,
            "predicted": predicted_id,
            "predicted_name": predicted_name,
            "top1": top1,
            "top3": top3,
            "parent_correct": parent,
            "notes": notes,
            "latency": elapsed,
            "predictions": predictions,
        })

    n = len(results)
    top1_acc = sum(r["top1"] for r in results) / n * 100
    top3_acc = sum(r["top3"] for r in results) / n * 100
    parent_acc = sum(r["parent_correct"] for r in results) / n * 100
    avg_lat = sum(latencies) / n

    return {
        "key": key,
        "label": label,
        "top1_acc": top1_acc,
        "top3_acc": top3_acc,
        "parent_acc": parent_acc,
        "avg_latency": avg_lat,
        "results": results,
    }


def print_summary(all_metrics: list[dict]) -> None:
    print("\n" + "=" * 80)
    print(f"{'Approach':<30} {'Top-1 Acc':>10} {'Top-3 Acc':>10} {'Parent Acc':>11} {'Avg Latency':>12}")
    print("-" * 80)
    for m in all_metrics:
        print(
            f"{m['label']:<30} {m['top1_acc']:>9.1f}% {m['top3_acc']:>9.1f}% "
            f"{m['parent_acc']:>10.1f}% {m['avg_latency']:>10.2f}s"
        )
    print("=" * 80)


def print_failures(metrics: dict) -> None:
    label = metrics["label"]
    failures = [r for r in metrics["results"] if not r["top1"]]
    if not failures:
        print(f"\n  {label}: No top-1 failures!")
        return
    print(f"\n  {label} — Top-1 failures ({len(failures)}/{len(metrics['results'])}):")
    for r in failures:
        top3_flag = " [in top3]" if r["top3"] else ""
        parent_flag = " [parent ok]" if r["parent_correct"] else ""
        print(f"    [{r['expected']}→{r['predicted']}]{top3_flag}{parent_flag}")
        print(f"      desc:     {r['description'][:80]}")
        print(f"      expected: {r['expected_name']}")
        print(f"      got:      {r['predicted_name']}")
        if r["predictions"]:
            top3_str = ", ".join(
                f"{p['category_number']}({p['confidence']:.2f})" for p in r["predictions"][:3]
            )
            print(f"      top-3:    {top3_str}")
        print()


def print_elderly_analysis(all_metrics: list[dict], cases: list) -> None:
    elderly_indices = [
        i for i, (_, _, notes) in enumerate(cases)
        if notes in ELDERLY_BOUNDARY_NOTES
        or "elderly" in notes.lower()
        or "senior" in notes.lower()
        or "aging" in notes.lower()
    ]
    if not elderly_indices:
        print("\n  No elderly cases found.")
        return

    print("\n" + "=" * 80)
    print("ELDERLY / HEALTHCARE BOUNDARY ANALYSIS")
    print("=" * 80)
    for m in all_metrics:
        print(f"\n  {m['label']}:")
        for i in elderly_indices:
            r = m["results"][i]
            status = "✓" if r["top1"] else "✗"
            print(f"    {status} [{r['expected']}] → [{r['predicted']}]  |  {r['notes']}")
            if not r["top1"]:
                print(f"         desc: {r['description'][:70]}")
                print(f"         want: {r['expected_name']}, got: {r['predicted_name']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approach", choices=list(APPROACH_MAP.keys()), help="Run one approach only")
    parser.add_argument("--elderly", action="store_true", help="Only run elderly boundary cases")
    parser.add_argument("--failures", action="store_true", help="Print detailed failure analysis")
    parser.add_argument("--log", action="store_true", help="Write results to a timestamped JSON file under tests/results/")
    parser.add_argument("--fresh", action="store_true", help="Run on fresh holdout cases instead of the original test set")
    args = parser.parse_args()

    if args.fresh:
        from tests.fresh_test_cases import FRESH_TEST_CASES
        cases = FRESH_TEST_CASES
        print(f"Running {len(cases)} FRESH holdout cases (overfitting check).")
    else:
        cases = TEST_CASES
    if args.elderly:
        cases = [
            c for c in TEST_CASES
            if "elderly" in c[2].lower() or "senior" in c[2].lower()
            or c[2] in ELDERLY_BOUNDARY_NOTES
        ]
        print(f"Running {len(cases)} elderly/boundary cases only.")

    approaches = (
        [(args.approach, APPROACH_MAP[args.approach][0])]
        if args.approach
        else [(k, v[0]) for k, v in APPROACH_MAP.items()]
    )

    all_metrics = []
    for key, label in approaches:
        print(f"\nRunning: {label} ...")
        m = evaluate_approach(key, label, cases)
        all_metrics.append(m)
        print(f"  done — top-1: {m['top1_acc']:.1f}%  top-3: {m['top3_acc']:.1f}%  avg: {m['avg_latency']:.2f}s")

    print_summary(all_metrics)
    print_elderly_analysis(all_metrics, cases)

    if args.failures:
        for m in all_metrics:
            print_failures(m)

    if args.log:
        write_log(all_metrics, cases)


def write_log(all_metrics: list[dict], cases: list) -> None:
    import json
    from datetime import datetime

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"eval_{timestamp}.json"

    payload = {
        "timestamp": timestamp,
        "num_cases": len(cases),
        "summary": [
            {
                "approach": m["label"],
                "top1_acc": round(m["top1_acc"], 2),
                "top3_acc": round(m["top3_acc"], 2),
                "parent_acc": round(m["parent_acc"], 2),
                "avg_latency_s": round(m["avg_latency"], 3),
            }
            for m in all_metrics
        ],
        "per_case": {
            m["label"]: [
                {
                    "description": r["description"],
                    "expected": r["expected"],
                    "predicted": r["predicted"],
                    "top1": r["top1"],
                    "top3": r["top3"],
                    "parent_correct": r["parent_correct"],
                    "notes": r["notes"],
                }
                for r in m["results"]
            ]
            for m in all_metrics
        },
    }

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nLog written to: {out_path}")


if __name__ == "__main__":
    main()
