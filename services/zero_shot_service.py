"""
Approach 2: Zero-shot NLI-based classification.
Uses a cross-encoder NLI model to score (description, category_label) pairs
without any training data. Works by framing classification as textual entailment.
"""

from transformers import pipeline

from utils.categories import help_categories, get_direct_children, get_category_hierarchy
from utils.categories_with_description import TAXONOMY


ZS_MODEL = "valhalla/distilbart-mnli-12-1"

_pipeline = None


def _is_leaf(category_id: str) -> bool:
    return len(get_direct_children(category_id)) == 0


def _build_label(category_id: str) -> str:
    name = help_categories.get(category_id, "")
    description = TAXONOMY.get(name, "")
    readable_name = name.replace("_", " ").title()
    if description:
        # Use a shorter label for NLI — just readable name + first sentence of description
        short_desc = description.split(".")[0]
        return f"{readable_name} — {short_desc}"
    return readable_name


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = pipeline("zero-shot-classification", model=ZS_MODEL)
    return _pipeline


def predict_categories(description: str, top_k: int = 3) -> tuple[list[dict], dict]:
    zs = _get_pipeline()

    leaf_ids = [cat_id for cat_id in help_categories if _is_leaf(cat_id)]
    labels = [_build_label(cat_id) for cat_id in leaf_ids]

    output = zs(description, candidate_labels=labels, multi_label=True)

    label_to_id = {_build_label(cat_id): cat_id for cat_id in leaf_ids}

    results = []
    for label, score in zip(output["labels"], output["scores"]):
        cat_id = label_to_id.get(label)
        if cat_id:
            cat_name = help_categories.get(cat_id, "")
            results.append({
                "category_number": cat_id,
                "category_name": cat_name,
                "confidence": float(score),
                "hierarchy": get_category_hierarchy(cat_id),
            })
        if len(results) >= top_k:
            break

    token_usage = {"provider": "zero-shot-nli", "model": ZS_MODEL, "total_tokens": 0}
    return results, token_usage
