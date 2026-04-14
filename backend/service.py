from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd

from backend.config import (
    EVALUATION_PATH,
    FEATURE_IMPORTANCE_PATH,
    METRICS_PATH,
    MODEL_COMPARISON_PATH,
    MODEL_PATH,
    SHAP_IMPORTANCE_PATH,
)
from backend.preprocess import (
    DEFAULT_PROFILE,
    FIELD_LABELS,
    RAW_FEATURE_COLUMNS,
    RiskBandThresholds,
    build_baseline_profile,
    format_feature_value,
    get_risk_band,
    load_dataset,
    prepare_inference_frame,
    split_features_target,
)


def sanitize_json_like(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_json_like(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json_like(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json_like(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return 0.0
        return value
    return value


@lru_cache(maxsize=1)
def load_model_bundle() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Model artifact not found. Run `python -m backend.train` or `python backend/train.py` first."
        )
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def load_metrics_summary() -> dict[str, Any]:
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_evaluation_summary() -> dict[str, Any]:
    if not EVALUATION_PATH.exists():
        return {}
    return json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_feature_importance() -> pd.DataFrame:
    if not FEATURE_IMPORTANCE_PATH.exists():
        return pd.DataFrame(columns=["feature", "importance", "importance_pct"])
    return pd.read_csv(FEATURE_IMPORTANCE_PATH)


@lru_cache(maxsize=1)
def load_shap_importance() -> pd.DataFrame:
    if not SHAP_IMPORTANCE_PATH.exists():
        return pd.DataFrame(columns=["feature", "mean_abs_shap"])
    return pd.read_csv(SHAP_IMPORTANCE_PATH)


@lru_cache(maxsize=1)
def load_model_comparison() -> pd.DataFrame:
    if not MODEL_COMPARISON_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(MODEL_COMPARISON_PATH)


@lru_cache(maxsize=1)
def load_scored_dataset() -> pd.DataFrame:
    dataframe = load_dataset()
    features, target = split_features_target(dataframe)
    bundle = load_model_bundle()

    probabilities = bundle["pipeline"].predict_proba(features)[:, 1]
    threshold = float(bundle.get("decision_threshold", 0.5))

    scored = dataframe.copy()
    scored["actual_churn_flag"] = target
    scored["churn_probability"] = probabilities
    scored["predicted_churn_flag"] = (probabilities >= threshold).astype(int)
    scored["predicted_label"] = np.where(scored["predicted_churn_flag"] == 1, "Yes", "No")
    scored["risk_band"] = pd.Categorical(
        [get_risk_band(probability, RiskBandThresholds()) for probability in probabilities],
        categories=["Low", "Medium", "High"],
        ordered=True,
    )
    scored["annual_revenue"] = pd.to_numeric(scored["MonthlyCharges"], errors="coerce").fillna(0) * 12
    return scored


def refresh_caches() -> None:
    load_model_bundle.cache_clear()
    load_metrics_summary.cache_clear()
    load_evaluation_summary.cache_clear()
    load_feature_importance.cache_clear()
    load_shap_importance.cache_clear()
    load_model_comparison.cache_clear()
    load_scored_dataset.cache_clear()


def build_factor_detail(feature_name: str, current_value: Any, baseline_value: Any, delta: float) -> str:
    current_label = format_feature_value(feature_name, current_value)
    baseline_label = format_feature_value(feature_name, baseline_value)
    impact_points = abs(delta) * 100

    if delta >= 0:
        return (
            f"{FIELD_LABELS.get(feature_name, feature_name)} is set to {current_label} instead of "
            f"{baseline_label}, increasing churn risk by about {impact_points:.1f} points."
        )

    return (
        f"{FIELD_LABELS.get(feature_name, feature_name)} at {current_label} is helping retention compared "
        f"with {baseline_label}, lowering churn risk by about {impact_points:.1f} points."
    )


def derive_local_factors(
    customer_profile: dict[str, Any],
    probability: float,
    pipeline: Any,
    baseline_profile: dict[str, Any],
    top_n: int = 4,
) -> list[dict[str, Any]]:
    influences: list[dict[str, Any]] = []

    for feature_name in RAW_FEATURE_COLUMNS:
        candidate_profile = customer_profile.copy()
        candidate_profile[feature_name] = baseline_profile[feature_name]
        candidate_frame = prepare_inference_frame(candidate_profile)
        candidate_probability = float(pipeline.predict_proba(candidate_frame)[:, 1][0])
        delta = probability - candidate_probability

        influences.append(
            {
                "title": FIELD_LABELS.get(feature_name, feature_name),
                "delta": round(delta, 4),
                "detail": build_factor_detail(
                    feature_name=feature_name,
                    current_value=customer_profile[feature_name],
                    baseline_value=baseline_profile[feature_name],
                    delta=delta,
                ),
            }
        )

    strongest = [item for item in influences if item["delta"] > 0.01]
    if strongest:
        ranked = sorted(strongest, key=lambda item: item["delta"], reverse=True)[:top_n]
        impact_type = "risk"
    else:
        ranked = sorted(influences, key=lambda item: item["delta"])[:top_n]
        impact_type = "protective"

    return [
        {
            "title": item["title"],
            "impact": round(abs(item["delta"]) * 100, 2),
            "impact_type": impact_type,
            "detail": item["detail"],
        }
        for item in ranked
    ]


def build_recommendation(probability: float, customer_profile: dict[str, Any]) -> str:
    if probability >= 0.65:
        if customer_profile["Contract"] == "Month-to-month":
            return "Prioritize a retention call and offer a contract upgrade or discount bundle within 24 hours."
        return "Escalate this account to the retention team and review support history before the next billing cycle."
    if probability >= 0.35:
        return "Trigger a targeted loyalty message, monitor engagement, and review price sensitivity this month."
    return "Keep the customer in standard monitoring and reinforce satisfaction with a low-touch loyalty message."


def predict_customer(payload: dict[str, Any] | None) -> dict[str, Any]:
    feature_frame = prepare_inference_frame(payload)
    customer_profile = feature_frame.iloc[0].to_dict()

    bundle = load_model_bundle()
    pipeline = bundle["pipeline"]
    threshold = float(bundle.get("decision_threshold", 0.5))

    probability = float(pipeline.predict_proba(feature_frame)[:, 1][0])
    predicted_flag = int(probability >= threshold)

    baseline_profile = bundle.get("baseline_profile") or build_baseline_profile(load_dataset())
    top_factors = derive_local_factors(customer_profile, probability, pipeline, baseline_profile)

    return {
        "model_name": bundle.get("model_name", bundle.get("best_model_name", "Unknown")),
        "trained_at_utc": bundle.get("trained_at_utc"),
        "prediction": "Likely to churn" if predicted_flag else "Likely to stay",
        "label": "Yes" if predicted_flag else "No",
        "churn_probability": round(probability, 4),
        "churn_probability_pct": round(probability * 100, 2),
        "risk_band": get_risk_band(probability, RiskBandThresholds()),
        "decision_threshold": round(threshold, 3),
        "recommended_action": build_recommendation(probability, customer_profile),
        "estimated_annual_revenue": round(float(customer_profile["MonthlyCharges"]) * 12, 2),
        "confidence_score": round(50 + abs(probability - threshold) * 100, 2),
        "customer_profile": customer_profile,
        "top_factors": top_factors,
    }


def build_analytics_payload(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        refresh_caches()

    scored = load_scored_dataset()
    bundle = load_model_bundle()
    metrics_summary = load_metrics_summary()
    evaluation = load_evaluation_summary()
    feature_importance = load_feature_importance()
    shap_importance = load_shap_importance()
    comparison = load_model_comparison()

    risk_distribution = (
        scored["risk_band"]
        .value_counts()
        .reindex(["Low", "Medium", "High"], fill_value=0)
        .rename_axis("label")
        .reset_index(name="count")
    )
    risk_distribution["pct"] = (risk_distribution["count"] / len(scored) * 100).round(2)

    tenure_trend = (
        scored.assign(
            TenureBand=pd.cut(
                pd.to_numeric(scored["tenure"], errors="coerce").fillna(0),
                bins=[-1, 12, 24, 48, 72, np.inf],
                labels=["0-12", "13-24", "25-48", "49-72", "72+"],
            )
        )
        .groupby("TenureBand", observed=False)
        .agg(
            customers=("customerID", "count"),
            actual_churn_rate=("actual_churn_flag", lambda values: round(values.mean() * 100, 2)),
            avg_predicted_risk=("churn_probability", lambda values: round(values.mean() * 100, 2)),
        )
        .fillna(0)
        .reset_index()
    )

    contract_hotspots = (
        scored.groupby("Contract", dropna=False)
        .agg(
            customers=("customerID", "count"),
            churn_rate=("actual_churn_flag", lambda values: round(values.mean() * 100, 2)),
            avg_risk=("churn_probability", lambda values: round(values.mean() * 100, 2)),
        )
        .sort_values(["churn_rate", "avg_risk"], ascending=False)
        .reset_index()
    )

    payment_hotspots = (
        scored.groupby("PaymentMethod", dropna=False)
        .agg(
            customers=("customerID", "count"),
            churn_rate=("actual_churn_flag", lambda values: round(values.mean() * 100, 2)),
            avg_risk=("churn_probability", lambda values: round(values.mean() * 100, 2)),
        )
        .sort_values(["churn_rate", "avg_risk"], ascending=False)
        .reset_index()
    )

    top_risk_customers = (
        scored[["customerID", "Contract", "PaymentMethod", "tenure", "MonthlyCharges", "churn_probability", "risk_band"]]
        .sort_values("churn_probability", ascending=False)
        .head(10)
        .rename(columns={"customerID": "customer_id"})
        .copy()
    )
    top_risk_customers["churn_probability"] = (top_risk_customers["churn_probability"] * 100).round(2)
    top_risk_customers["MonthlyCharges"] = pd.to_numeric(top_risk_customers["MonthlyCharges"], errors="coerce").round(2)

    segment_rules = [
        ("At-Risk Newcomers", (scored["tenure"] <= 12) & (scored["MonthlyCharges"] >= 70)),
        ("Loyal Revenue Base", (scored["tenure"] >= 48) & (scored["MonthlyCharges"] >= 70)),
        ("Digital Billing Watchlist", scored["PaymentMethod"].eq("Electronic check") & scored["PaperlessBilling"].eq("Yes")),
        ("Support Gap Watchlist", scored["OnlineSecurity"].eq("No") & scored["TechSupport"].eq("No")),
    ]
    segments: list[dict[str, Any]] = []
    for label, mask in segment_rules:
        subset = scored.loc[mask]
        if subset.empty:
            continue
        segments.append(
            {
                "label": label,
                "customers": int(len(subset)),
                "avg_risk": round(float(subset["churn_probability"].mean() * 100), 2),
                "avg_tenure": round(float(pd.to_numeric(subset["tenure"], errors="coerce").mean()), 2),
                "avg_monthly_charge": round(float(pd.to_numeric(subset["MonthlyCharges"], errors="coerce").mean()), 2),
            }
        )

    model_metrics = bundle.get("metrics", {})
    confusion_matrix = evaluation.get("confusion_matrix", [[0, 0], [0, 0]])

    payload = {
        "overview": {
            "total_customers": int(len(scored)),
            "actual_churn_rate": round(float(scored["actual_churn_flag"].mean() * 100), 2),
            "predicted_high_risk": int(scored["risk_band"].eq("High").sum()),
            "avg_tenure": round(float(pd.to_numeric(scored["tenure"], errors="coerce").mean()), 2),
            "avg_monthly_charge": round(float(pd.to_numeric(scored["MonthlyCharges"], errors="coerce").mean()), 2),
        },
        "model": {
            "name": bundle.get("model_name", bundle.get("best_model_name", "Unknown")),
            "decision_threshold": round(float(bundle.get("decision_threshold", 0.5)), 3),
            "metrics": {
                "accuracy": round(float(model_metrics.get("accuracy", 0.0)) * 100, 2),
                "precision": round(float(model_metrics.get("precision", 0.0)) * 100, 2),
                "recall": round(float(model_metrics.get("recall", 0.0)) * 100, 2),
                "f1_score": round(float(model_metrics.get("f1_score", 0.0)) * 100, 2),
                "roc_auc": round(float(model_metrics.get("roc_auc", 0.0)) * 100, 2),
            },
            "trained_at_utc": bundle.get("trained_at_utc"),
            "confusion_matrix": confusion_matrix,
        },
        "risk_distribution": risk_distribution.to_dict(orient="records"),
        "tenure_trend": tenure_trend.to_dict(orient="records"),
        "contract_hotspots": contract_hotspots.to_dict(orient="records"),
        "payment_hotspots": payment_hotspots.to_dict(orient="records"),
        "top_risk_customers": top_risk_customers.to_dict(orient="records"),
        "feature_importance": feature_importance.head(12).to_dict(orient="records"),
        "shap_importance": shap_importance.head(12).to_dict(orient="records"),
        "model_comparison": comparison.to_dict(orient="records") if not comparison.empty else metrics_summary.get("model_results", []),
        "segments": segments,
        "form_defaults": DEFAULT_PROFILE,
    }
    return sanitize_json_like(payload)
