from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from backend.bias.analysis import (
    compute_class_imbalance,
    compute_distribution_analysis,
    compute_fairness_metrics,
    compute_group_comparison,
    compute_numeric_skewness,
    compute_trust_score,
    detect_proxy_features,
    encode_binary_target,
    infer_target_column,
)
from backend.bias.explainability import generate_explainability_insights
from backend.bias.profiling import profile_dataset
from backend.bias.recommendations import build_recommendations


def run_bias_pipeline(
    dataframe: pd.DataFrame,
    *,
    dataset_name: str,
    ingestion_summary: dict[str, Any],
) -> dict[str, Any]:
    profile = profile_dataset(dataframe, ingestion_summary)

    target_column = infer_target_column(dataframe)
    target_info = encode_binary_target(dataframe, target_column)
    class_imbalance = compute_class_imbalance(target_info)

    sensitive_attributes = profile.get("sensitive_attributes", [])
    distribution_analysis = compute_distribution_analysis(dataframe, sensitive_attributes)
    group_comparison = compute_group_comparison(dataframe, sensitive_attributes, target_info)
    fairness_metrics = compute_fairness_metrics(group_comparison)
    proxy_bias = detect_proxy_features(dataframe, sensitive_attributes)
    skewness = compute_numeric_skewness(dataframe)

    trust = compute_trust_score(
        fairness_metrics=fairness_metrics,
        class_imbalance=class_imbalance,
        distribution=distribution_analysis,
        proxy_features=proxy_bias,
    )

    summary_for_llm = {
        "profile": profile,
        "target_info": {
            "target_column": target_info.get("target_column"),
            "target_available": target_info.get("target_available"),
            "class_mapping": target_info.get("class_mapping"),
        },
        "class_imbalance": class_imbalance,
        "distribution_analysis": distribution_analysis,
        "group_comparison": group_comparison,
        "fairness_metrics": fairness_metrics,
        "proxy_bias": proxy_bias,
        "skewness": skewness,
        "trust": trust,
    }

    explainability = generate_explainability_insights(summary_for_llm)
    summary_for_llm["explainability_source"] = explainability.get("source")
    recommendations = build_recommendations(summary_for_llm)

    metrics = {
        "demographic_parity_difference": fairness_metrics.get("demographic_parity_difference", 0.0),
        "disparate_impact_ratio": fairness_metrics.get("disparate_impact_ratio", 1.0),
        "statistical_parity": fairness_metrics.get("statistical_parity", 1.0),
        "representation_imbalance_score": fairness_metrics.get("representation_imbalance_score", 0.0),
        "class_balance_ratio": class_imbalance.get("class_balance_ratio", 1.0),
        "proxy_feature_count": proxy_bias.get("proxy_feature_count", 0),
    }

    return {
        "dataset_name": dataset_name,
        "bias_risk": trust["risk_level"],
        "trust_score": trust["trust_score"],
        "sensitive_attributes": sensitive_attributes,
        "metrics": metrics,
        "insights": explainability.get("insights", ""),
        "recommendations": recommendations,
        "details": {
            "profile": profile,
            "target_info": {
                "target_column": target_info.get("target_column"),
                "target_available": target_info.get("target_available"),
                "reason": target_info.get("reason"),
                "class_mapping": target_info.get("class_mapping"),
            },
            "distribution_analysis": distribution_analysis,
            "group_comparison": group_comparison,
            "fairness_metrics": fairness_metrics,
            "proxy_bias": proxy_bias,
            "class_imbalance": class_imbalance,
            "skewness": skewness,
            "trust": trust,
            "explainability_source": explainability.get("source"),
            "explainability_note": explainability.get("note"),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    }

