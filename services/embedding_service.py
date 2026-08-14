"""
Approach 1: Embedding-based similarity search.
Pre-computes sentence-transformer embeddings for every leaf category,
then at inference time finds the closest categories by cosine similarity.
No LLM calls required.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from utils.categories import help_categories, get_direct_children, get_category_hierarchy
from utils.categories_with_description import TAXONOMY
from utils.routing_for_categories import is_elderly_context


MODEL_NAME = "all-MiniLM-L6-v2"

# When elderly context is detected, the "boost" strategy adds this much to the
# cosine similarity of every 6.* (elderly) leaf before ranking. Tuned empirically.
ELDERLY_BOOST = 0.15

_model = None
_category_ids: list[str] = []
_category_texts: list[str] = []
_embeddings: np.ndarray | None = None


def _is_leaf(category_id: str) -> bool:
    return len(get_direct_children(category_id)) == 0


def _build_category_text(category_id: str) -> str:
    name = help_categories.get(category_id, "")
    description = TAXONOMY.get(name, "")
    readable_name = name.replace("_", " ").title()
    if description:
        return f"{readable_name}: {description}"
    return readable_name


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_index() -> tuple[list[str], np.ndarray]:
    global _category_ids, _category_texts, _embeddings
    if _embeddings is not None:
        return _category_ids, _embeddings

    model = _get_model()

    ids = []
    texts = []
    for cat_id in help_categories:
        if _is_leaf(cat_id):
            ids.append(cat_id)
            texts.append(_build_category_text(cat_id))

    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    _category_ids = ids
    _category_texts = texts
    _embeddings = embeddings
    return _category_ids, _embeddings


def predict_categories(
    description: str, top_k: int = 3, elderly_strategy: str | None = None
) -> tuple[list[dict], dict]:
    """Rank leaf categories by cosine similarity to the description.

    elderly_strategy controls how elderly context is handled:
      - None     : no special handling (pure semantic similarity).
      - "boost"  : when is_elderly_context() fires, add ELDERLY_BOOST to the
                   similarity of every 6.* leaf, then rank as usual.
      - "route"  : when is_elderly_context() fires, score ONLY the 6.* leaves.
    """
    model = _get_model()
    cat_ids, cat_embeddings = _get_index()

    query_embedding = model.encode([description], convert_to_numpy=True, normalize_embeddings=True)
    similarities = cosine_similarity(query_embedding, cat_embeddings)[0].copy()

    elderly_triggered = (
        elderly_strategy in ("boost", "route") and is_elderly_context(description)
    )
    elderly_mask = np.array([cid.startswith("6.") for cid in cat_ids])

    if elderly_triggered and elderly_strategy == "boost":
        similarities[elderly_mask] += ELDERLY_BOOST
    elif elderly_triggered and elderly_strategy == "route":
        # Exclude non-elderly leaves from consideration entirely.
        similarities[~elderly_mask] = -np.inf

    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if not np.isfinite(similarities[idx]):
            continue
        cat_id = cat_ids[idx]
        cat_name = help_categories.get(cat_id, "")
        results.append({
            "category_number": cat_id,
            "category_name": cat_name,
            "confidence": float(min(1.0, similarities[idx])),
            "hierarchy": get_category_hierarchy(cat_id),
        })

    token_usage = {"provider": "embedding", "model": MODEL_NAME, "total_tokens": 0}
    return results, token_usage
