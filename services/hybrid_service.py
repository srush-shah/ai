"""
Approach 3: Hybrid — embedding retrieval + LLM final ranking.
Embeddings narrow to top-N leaf candidates (no hierarchy traversal needed),
then a single LLM call picks the best match.
Reduces LLM calls from ~3 (current hierarchical) to 1.
"""

import json
import numpy as np

from services.embedding_service import _get_model, _get_index
from utils.categories import help_categories, get_category_hierarchy
from utils.categories_with_description import TAXONOMY
from utils.client import client, _use_groq, _gemini_client


CANDIDATE_POOL = 10
LLM_MODEL = "llama-3.1-8b-instant"
GEMINI_MODEL = "gemini-2.0-flash"


def _build_prompt(description: str, candidates: list[str]) -> str:
    lines = [
        "You are a zero-shot classifier.",
        "Return JSON only with a key 'categories' containing a ranked list.",
        "For each item include the category ID and a confidence score (0.0 to 1.0).",
        "Return the top 3 most relevant categories.",
        "Choose only from the candidate IDs listed below.",
        "",
        "Candidates:",
    ]
    for cat_id in candidates:
        name = help_categories.get(cat_id, "")
        desc = TAXONOMY.get(name, "")
        readable = name.replace("_", " ").title()
        if desc:
            lines.append(f"  {cat_id}: {readable} — {desc}")
        else:
            lines.append(f"  {cat_id}: {readable}")

    lines += [
        "",
        f"Description: {description}",
        "",
        'Return format: {"categories": [{"category": "ID", "confidence": 0.95}, ...]}',
    ]
    return "\n".join(lines)


def _extract_groq_usage(response) -> dict:
    usage = getattr(response, "usage", None)
    if not usage:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
        "completion_tokens": getattr(usage, "completion_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
    }


def _call_llm(prompt: str, candidate_set: set[str]) -> list[dict]:
    if _use_groq and client:
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                top_p=0.3,
                response_format={"type": "json_object"},
            )
            usage = _extract_groq_usage(response)
            raw = response.choices[0].message.content or ""
            data = json.loads(raw)
            return _parse_results(data, candidate_set), usage
        except Exception as e:
            print(f"Hybrid LOG: Groq failed: {e}")

    if _gemini_client:
        response = _gemini_client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt
        )
        text = (response.text or "").strip()
        if text.startswith("{"):
            data = json.loads(text)
            return _parse_results(data, candidate_set), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _parse_results(data: dict, candidate_set: set[str]) -> list[dict]:
    categories = data.get("categories", [])
    if not categories and "category" in data:
        categories = [{"category": data["category"], "confidence": data.get("confidence", 0.0)}]

    results = []
    for item in categories:
        cat_id = item.get("category") if isinstance(item, dict) else item
        confidence = float(item.get("confidence", 0.0)) if isinstance(item, dict) else 0.0
        if cat_id in candidate_set:
            results.append({
                "category_number": cat_id,
                "category_name": help_categories.get(cat_id, ""),
                "confidence": max(0.0, min(1.0, confidence)),
                "hierarchy": get_category_hierarchy(cat_id),
            })
    return results


def predict_categories(description: str, top_k: int = 3) -> tuple[list[dict], dict]:
    from sklearn.metrics.pairwise import cosine_similarity

    model = _get_model()
    cat_ids, cat_embeddings = _get_index()

    query_emb = model.encode([description], convert_to_numpy=True, normalize_embeddings=True)
    sims = cosine_similarity(query_emb, cat_embeddings)[0]
    pool_indices = np.argsort(sims)[::-1][:CANDIDATE_POOL]
    candidates = [cat_ids[i] for i in pool_indices]
    candidate_set = set(candidates)

    prompt = _build_prompt(description, candidates)
    results, llm_usage = _call_llm(prompt, candidate_set)

    token_usage = {
        "provider": "hybrid",
        "embedding_model": "all-MiniLM-L6-v2",
        "llm_model": LLM_MODEL,
        **llm_usage,
    }

    if not results:
        for idx in pool_indices[:top_k]:
            cat_id = cat_ids[idx]
            results.append({
                "category_number": cat_id,
                "category_name": help_categories.get(cat_id, ""),
                "confidence": float(sims[idx]),
                "hierarchy": get_category_hierarchy(cat_id),
            })

    return results[:top_k], token_usage
