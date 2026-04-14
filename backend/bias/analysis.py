from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.bias.constants import TARGET_COLUMN_CANDIDATES


def _bucket_sensitive_series(column_name: str, series: pd.Series) -> pd.Series:
    lowered_name = column_name.lower()
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce")
        if "age" in lowered_name:
            bins = [-np.inf, 18, 30, 45, 60, np.inf]
            labels = ["<=18", "19-30", "31-45", "46-60", "60+"]
            bucketed = pd.cut(numeric, bins=bins, labels=labels, include_lowest=True)
            return bucketed.astype(str)

        if "income" in lowered_name or numeric.nunique(dropna=True) > 12:
            try:
                bucketed = pd.qcut(numeric, q=4, duplicates="drop")
            except ValueError:
                bucketed = pd.cut(numeric, bins=4)
            return bucketed.astype(str)

        rounded = numeric.round(0)
        return rounded.astype(str)

    return series.astype(str).fillna("unknown")


def infer_target_column(dataframe: pd.DataFrame) -> str | None:
    columns = dataframe.columns.tolist()
    lowered_map = {column.lower(): column for column in columns}

    for candidate in TARGET_COLUMN_CANDIDATES:
        if candidate in lowered_map:
            return lowered_map[candidate]

    for column in columns:
        lowered = column.lower()
        if any(candidate in lowered for candidate in TARGET_COLUMN_CANDIDATES):
            return column

    categorical_candidates = [
        column
        for column in columns
        if not pd.api.types.is_numeric_dtype(dataframe[column]) and 1 < dataframe[column].nunique() <= 10
    ]
    if categorical_candidates:
        return categorical_candidates[-1]

    numeric_candidates = [
        column
        for column in columns
        if pd.api.types.is_numeric_dtype(dataframe[column]) and 1 < dataframe[column].nunique() <= 5
    ]
    if numeric_candidates:
        return numeric_candidates[-1]

    return None


def encode_binary_target(dataframe: pd.DataFrame, target_column: str | None) -> dict[str, Any]:
    if target_column is None:
        return {
            "target_column": None,
            "target_available": False,
            "reason": "No suitable target column found.",
            "target_series": None,
            "class_mapping": {},
        }

    series = dataframe[target_column]
    numeric = pd.to_numeric(series, errors="coerce")

    if pd.api.types.is_numeric_dtype(series) or numeric.notna().all():
        unique_values = sorted(numeric.dropna().unique().tolist())
        if len(unique_values) < 2:
            return {
                "target_column": target_column,
                "target_available": False,
                "reason": "Target column has a single class.",
                "target_series": None,
                "class_mapping": {},
            }

        positive_label = unique_values[-1]
        encoded = (numeric == positive_label).astype(int)
        return {
            "target_column": target_column,
            "target_available": True,
            "reason": "Numeric target encoded using the highest value as positive class.",
            "target_series": encoded,
            "class_mapping": {"positive": str(positive_label), "negative": "all_other_values"},
        }

    categorical = series.astype(str).fillna("unknown")
    value_counts = categorical.value_counts()
    if value_counts.size < 2:
        return {
            "target_column": target_column,
            "target_available": False,
            "reason": "Target column has a single class.",
            "target_series": None,
            "class_mapping": {},
        }

    positive_label = value_counts.index[-1]
    encoded = (categorical == positive_label).astype(int)
    return {
        "target_column": target_column,
        "target_available": True,
        "reason": "Categorical target encoded using least frequent class as positive class.",
        "target_series": encoded,
        "class_mapping": {"positive": str(positive_label), "negative": "all_other_values"},
    }


def compute_class_imbalance(target_info: dict[str, Any]) -> dict[str, Any]:
    target_series = target_info.get("target_series")
    if target_series is None:
        return {
            "available": False,
            "majority_class_count": None,
            "minority_class_count": None,
            "class_balance_ratio": 1.0,
            "positive_rate": None,
            "message": target_info.get("reason", "Class imbalance could not be computed."),
        }

    counts = target_series.value_counts().to_dict()
    majority = max(counts.values())
    minority = min(counts.values())
    ratio = float(minority / majority) if majority else 1.0

    return {
        "available": True,
        "majority_class_count": int(majority),
        "minority_class_count": int(minority),
        "class_balance_ratio": round(ratio, 6),
        "positive_rate": round(float(target_series.mean()), 6),
        "message": "Class distribution computed from inferred target column.",
    }


def compute_distribution_analysis(dataframe: pd.DataFrame, sensitive_attributes: list[str]) -> dict[str, Any]:
    by_attribute: dict[str, Any] = {}
    underrepresented_groups: list[dict[str, Any]] = []
    overrepresented_groups: list[dict[str, Any]] = []

    total_rows = max(len(dataframe), 1)

    for attribute in sensitive_attributes:
        grouped_series = _bucket_sensitive_series(attribute, dataframe[attribute])
        counts = grouped_series.value_counts(dropna=False)
        proportions = counts / total_rows
        expected_share = 1 / max(len(counts), 1)

        groups = []
        for group_name, count in counts.items():
            share = float(proportions[group_name])
            group_payload = {
                "group": str(group_name),
                "count": int(count),
                "percentage": round(share * 100, 4),
            }
            groups.append(group_payload)

            if share < expected_share * 0.8:
                underrepresented_groups.append({"attribute": attribute, **group_payload})
            elif share > expected_share * 1.2:
                overrepresented_groups.append({"attribute": attribute, **group_payload})

        by_attribute[attribute] = {
            "group_count": int(len(counts)),
            "expected_uniform_share_pct": round(expected_share * 100, 4),
            "groups": groups,
        }

    return {
        "by_attribute": by_attribute,
        "underrepresented_groups": underrepresented_groups,
        "overrepresented_groups": overrepresented_groups,
    }


def compute_group_comparison(
    dataframe: pd.DataFrame,
    sensitive_attributes: list[str],
    target_info: dict[str, Any],
) -> dict[str, Any]:
    target_series = target_info.get("target_series")
    if target_series is None:
        return {"available": False, "by_attribute": {}}

    by_attribute: dict[str, Any] = {}
    for attribute in sensitive_attributes:
        grouped_series = _bucket_sensitive_series(attribute, dataframe[attribute])
        comparison_frame = pd.DataFrame({"group": grouped_series, "target": target_series})

        aggregated = (
            comparison_frame.groupby("group", dropna=False)
            .agg(count=("target", "size"), positive_rate=("target", "mean"))
            .reset_index()
        )
        aggregated["positive_rate"] = aggregated["positive_rate"].round(6)

        by_attribute[attribute] = {
            "groups": [
                {
                    "group": str(row["group"]),
                    "count": int(row["count"]),
                    "positive_rate": float(row["positive_rate"]),
                }
                for _, row in aggregated.iterrows()
            ]
        }

    return {"available": True, "by_attribute": by_attribute}


def _representation_imbalance_from_counts(counts: list[int]) -> float:
    if not counts:
        return 0.0
    total = sum(counts)
    if total == 0:
        return 0.0
    observed = np.array(counts, dtype=float) / total
    expected = np.full_like(observed, fill_value=1 / len(observed))
    score = float(np.sum(np.abs(observed - expected)) / 2)
    return max(0.0, min(1.0, score))


def compute_fairness_metrics(group_comparison: dict[str, Any]) -> dict[str, Any]:
    if not group_comparison.get("available"):
        return {
            "demographic_parity_difference": 0.0,
            "disparate_impact_ratio": 1.0,
            "statistical_parity": 1.0,
            "representation_imbalance_score": 0.0,
            "by_sensitive_attribute": {},
            "note": "Fairness metrics were neutral because no target column was available.",
        }

    by_attribute_metrics: dict[str, Any] = {}
    all_dpd: list[float] = []
    all_dir: list[float] = []
    all_statistical_parity: list[float] = []
    all_representation: list[float] = []

    for attribute, payload in group_comparison["by_attribute"].items():
        groups = payload.get("groups", [])
        rates = [float(group["positive_rate"]) for group in groups]
        counts = [int(group["count"]) for group in groups]
        if len(rates) < 2:
            continue

        max_rate = max(rates)
        min_rate = min(rates)
        dpd = float(max_rate - min_rate)
        dir_ratio = float(min_rate / max_rate) if max_rate > 0 else 1.0

        weighted_rate = float(np.average(rates, weights=counts))
        avg_deviation = float(np.mean([abs(rate - weighted_rate) for rate in rates]))
        statistical_parity = max(0.0, min(1.0, 1 - avg_deviation))

        representation_score = _representation_imbalance_from_counts(counts)

        by_attribute_metrics[attribute] = {
            "demographic_parity_difference": round(dpd, 6),
            "disparate_impact_ratio": round(dir_ratio, 6),
            "statistical_parity": round(statistical_parity, 6),
            "representation_imbalance_score": round(representation_score, 6),
        }
        all_dpd.append(dpd)
        all_dir.append(dir_ratio)
        all_statistical_parity.append(statistical_parity)
        all_representation.append(representation_score)

    if not by_attribute_metrics:
        return {
            "demographic_parity_difference": 0.0,
            "disparate_impact_ratio": 1.0,
            "statistical_parity": 1.0,
            "representation_imbalance_score": 0.0,
            "by_sensitive_attribute": {},
            "note": "Fairness metrics were neutral because sensitive groups were insufficient for comparison.",
        }

    return {
        "demographic_parity_difference": round(max(all_dpd), 6),
        "disparate_impact_ratio": round(min(all_dir), 6),
        "statistical_parity": round(float(np.mean(all_statistical_parity)), 6),
        "representation_imbalance_score": round(float(np.mean(all_representation)), 6),
        "by_sensitive_attribute": by_attribute_metrics,
    }


def detect_proxy_features(
    dataframe: pd.DataFrame,
    sensitive_attributes: list[str],
    threshold: float = 0.6,
) -> dict[str, Any]:
    if not sensitive_attributes:
        return {
            "threshold": threshold,
            "proxy_feature_count": 0,
            "proxy_features": [],
            "top_correlations": [],
        }

    encoded = pd.DataFrame(index=dataframe.index)
    for column in dataframe.columns:
        if pd.api.types.is_numeric_dtype(dataframe[column]):
            numeric = pd.to_numeric(dataframe[column], errors="coerce")
            encoded[column] = numeric.fillna(numeric.median() if not numeric.isna().all() else 0.0)
        else:
            encoded[column] = pd.factorize(dataframe[column].astype(str))[0]

    correlation_matrix = encoded.corr().fillna(0.0)
    proxy_rows: list[dict[str, Any]] = []

    for sensitive in sensitive_attributes:
        if sensitive not in correlation_matrix.columns:
            continue
        for feature in correlation_matrix.columns:
            if feature == sensitive or feature in sensitive_attributes:
                continue
            value = float(correlation_matrix.loc[sensitive, feature])
            if abs(value) >= threshold:
                proxy_rows.append(
                    {
                        "sensitive_attribute": sensitive,
                        "feature": feature,
                        "correlation": round(value, 6),
                        "abs_correlation": round(abs(value), 6),
                    }
                )

    proxy_rows.sort(key=lambda item: item["abs_correlation"], reverse=True)

    return {
        "threshold": threshold,
        "proxy_feature_count": len(proxy_rows),
        "proxy_features": proxy_rows[:40],
        "top_correlations": proxy_rows[:12],
    }


def compute_numeric_skewness(dataframe: pd.DataFrame) -> dict[str, Any]:
    numeric_columns = dataframe.select_dtypes(include=[np.number]).columns.tolist()
    skew_payload: list[dict[str, Any]] = []
    for column in numeric_columns:
        series = pd.to_numeric(dataframe[column], errors="coerce")
        if series.nunique(dropna=True) < 3:
            continue
        skew_value = float(series.skew())
        skew_payload.append(
            {
                "column": column,
                "skewness": round(skew_value, 6),
                "severity": "high" if abs(skew_value) >= 1 else "moderate" if abs(skew_value) >= 0.5 else "low",
            }
        )

    skew_payload.sort(key=lambda item: abs(item["skewness"]), reverse=True)
    return {"columns": skew_payload[:30]}


def compute_trust_score(
    fairness_metrics: dict[str, Any],
    class_imbalance: dict[str, Any],
    distribution: dict[str, Any],
    proxy_features: dict[str, Any],
) -> dict[str, Any]:
    dpd = float(fairness_metrics.get("demographic_parity_difference", 0.0))
    dir_ratio = float(fairness_metrics.get("disparate_impact_ratio", 1.0))
    statistical_parity = float(fairness_metrics.get("statistical_parity", 1.0))
    representation_score = float(fairness_metrics.get("representation_imbalance_score", 0.0))
    class_balance = float(class_imbalance.get("class_balance_ratio", 1.0))
    proxy_count = int(proxy_features.get("proxy_feature_count", 0))

    penalties = {
        "demographic_parity_penalty": max(0.0, dpd * 35),
        "disparate_impact_penalty": max(0.0, ((0.8 - dir_ratio) / 0.8) * 25) if dir_ratio < 0.8 else 0.0,
        "statistical_parity_penalty": max(0.0, ((0.85 - statistical_parity) / 0.85) * 12)
        if statistical_parity < 0.85
        else 0.0,
        "representation_penalty": max(0.0, representation_score * 18),
        "class_imbalance_penalty": max(0.0, (1 - class_balance) * 15),
        "proxy_bias_penalty": min(float(proxy_count) * 1.5, 18.0),
        "group_distribution_penalty": min(
            float(len(distribution.get("underrepresented_groups", []))) * 1.2,
            12.0,
        ),
    }

    total_penalty = float(sum(penalties.values()))
    trust_score = max(0.0, min(100.0, 100.0 - total_penalty))

    if trust_score <= 40:
        risk_level = "High"
    elif trust_score <= 70:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "trust_score": round(trust_score, 2),
        "risk_level": risk_level,
        "penalties": {name: round(value, 4) for name, value in penalties.items()},
    }

