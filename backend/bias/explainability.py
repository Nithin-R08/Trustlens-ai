from __future__ import annotations

import json
import os
from typing import Any

from backend.bias.constants import EXPLAINABILITY_PROMPT

try:
    import requests
except Exception:  # pragma: no cover - dependency may be optional in constrained environments
    requests = None


def _build_fallback_insight(summary: dict[str, Any]) -> str:
    fairness = summary.get("fairness_metrics", {})
    trust = summary.get("trust", {})
    distribution = summary.get("distribution_analysis", {})
    proxy = summary.get("proxy_bias", {})

    underrepresented = distribution.get("underrepresented_groups", [])
    proxy_count = proxy.get("proxy_feature_count", 0)
    dpd = fairness.get("demographic_parity_difference", 0.0)
    dir_ratio = fairness.get("disparate_impact_ratio", 1.0)
    trust_score = trust.get("trust_score", 0)
    risk_level = trust.get("risk_level", "Medium")

    affected_group_phrase = "No major underrepresented groups were detected."
    if underrepresented:
        top = underrepresented[0]
        affected_group_phrase = (
            f"Underrepresentation is most visible for `{top['attribute']}` = `{top['group']}` "
            f"({top['percentage']}% of the dataset)."
        )

    proxy_phrase = (
        f"{proxy_count} potential proxy feature(s) were detected, which can indirectly encode sensitive traits."
        if proxy_count
        else "No strong proxy features were detected above the configured correlation threshold."
    )

    return (
        f"TrustLens AI assessed this dataset as {risk_level} risk with a trust score of {trust_score}. "
        f"Fairness indicators show demographic parity difference at {dpd} and disparate impact ratio at {dir_ratio}. "
        f"{affected_group_phrase} {proxy_phrase} "
        "Recommended mitigation focuses on improving representation balance, auditing high-correlation proxy columns, "
        "and reweighting or resampling during model training to maintain parity across groups."
    )


def _call_mistral(summary: dict[str, Any]) -> str | None:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key or requests is None:
        return None

    api_url = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")
    model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

    condensed_summary = {
        "profile": summary.get("profile", {}),
        "fairness_metrics": summary.get("fairness_metrics", {}),
        "distribution_analysis": {
            "underrepresented_groups": summary.get("distribution_analysis", {}).get("underrepresented_groups", []),
            "overrepresented_groups": summary.get("distribution_analysis", {}).get("overrepresented_groups", []),
        },
        "proxy_bias": summary.get("proxy_bias", {}).get("top_correlations", []),
        "trust": summary.get("trust", {}),
    }

    user_message = (
        f"{EXPLAINABILITY_PROMPT}\n\n"
        f"Dataset summary:\n{json.dumps(condensed_summary, indent=2)}"
    )

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "You are a practical AI fairness and data governance advisor."},
            {"role": "user", "content": user_message},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(api_url, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def generate_explainability_insights(summary: dict[str, Any]) -> dict[str, Any]:
    try:
        llm_output = _call_mistral(summary)
        if llm_output:
            return {"insights": llm_output, "source": "mistral"}
    except Exception as error:  # pragma: no cover - network/runtime dependent
        fallback = _build_fallback_insight(summary)
        return {
            "insights": fallback,
            "source": "rule_based_fallback",
            "note": f"LLM unavailable, fallback used: {error}",
        }

    return {
        "insights": _build_fallback_insight(summary),
        "source": "rule_based_fallback",
    }

