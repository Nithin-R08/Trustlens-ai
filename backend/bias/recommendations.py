from __future__ import annotations

from typing import Any


def build_recommendations(summary: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []

    fairness = summary.get("fairness_metrics", {})
    distribution = summary.get("distribution_analysis", {})
    proxy = summary.get("proxy_bias", {})
    class_imbalance = summary.get("class_imbalance", {})

    if class_imbalance.get("available") and class_imbalance.get("class_balance_ratio", 1.0) < 0.6:
        recommendations.append(
            "Balance the target classes using stratified resampling or class weights before model training."
        )

    if distribution.get("underrepresented_groups"):
        recommendations.append(
            "Collect or synthesize additional records for underrepresented sensitive groups to reduce representation gaps."
        )

    if fairness.get("demographic_parity_difference", 0.0) > 0.15:
        recommendations.append(
            "Apply pre-processing reweighting and evaluate threshold optimization to reduce demographic parity gaps."
        )

    if fairness.get("disparate_impact_ratio", 1.0) < 0.8:
        recommendations.append(
            "Investigate disparate impact by group and calibrate decision thresholds with fairness constraints."
        )

    if proxy.get("proxy_feature_count", 0) > 0:
        recommendations.append(
            "Audit and remove or transform high-correlation proxy features that indirectly encode sensitive attributes."
        )

    skewness_columns = summary.get("skewness", {}).get("columns", [])
    highly_skewed = [item["column"] for item in skewness_columns if item.get("severity") == "high"]
    if highly_skewed:
        recommendations.append(
            "Apply robust scaling or log transforms to heavily skewed numeric features before training."
        )

    if not summary.get("profile", {}).get("sensitive_attributes"):
        recommendations.append(
            "Add explicit sensitive attribute columns (where legally and ethically permitted) to improve fairness audits."
        )

    if not recommendations:
        recommendations.append(
            "Maintain current data governance controls and continue periodic fairness monitoring before each model retrain."
        )

    return recommendations

