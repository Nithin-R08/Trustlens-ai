from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.bias.constants import SENSITIVE_ATTRIBUTE_KEYWORDS


def detect_column_types(dataframe: pd.DataFrame) -> dict[str, list[str]]:
    numeric_columns = dataframe.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = [column for column in dataframe.columns if column not in numeric_columns]
    return {
        "numeric": numeric_columns,
        "categorical": categorical_columns,
    }


def identify_sensitive_attributes(columns: list[str]) -> list[str]:
    sensitive: list[str] = []
    for column in columns:
        lowered = column.lower()
        for keywords in SENSITIVE_ATTRIBUTE_KEYWORDS.values():
            if any(keyword in lowered for keyword in keywords):
                sensitive.append(column)
                break
    return sorted(set(sensitive))


def build_summary_statistics(dataframe: pd.DataFrame, column_types: dict[str, list[str]]) -> dict[str, Any]:
    numeric_summary: dict[str, dict[str, float]] = {}
    for column in column_types["numeric"]:
        series = pd.to_numeric(dataframe[column], errors="coerce")
        numeric_summary[column] = {
            "mean": round(float(series.mean()), 6),
            "median": round(float(series.median()), 6),
            "std": round(float(series.std(ddof=0)), 6),
            "min": round(float(series.min()), 6),
            "max": round(float(series.max()), 6),
            "skewness": round(float(series.skew()), 6) if len(series) > 2 else 0.0,
        }

    categorical_summary: dict[str, dict[str, Any]] = {}
    for column in column_types["categorical"]:
        series = dataframe[column].astype(str)
        value_counts = series.value_counts(dropna=False).head(8)
        categorical_summary[column] = {
            "unique_values": int(series.nunique(dropna=False)),
            "top_values": [
                {"value": str(index), "count": int(count)}
                for index, count in value_counts.items()
            ],
        }

    return {
        "numeric": numeric_summary,
        "categorical": categorical_summary,
    }


def profile_dataset(dataframe: pd.DataFrame, ingestion_summary: dict[str, Any]) -> dict[str, Any]:
    column_types = detect_column_types(dataframe)
    sensitive_attributes = identify_sensitive_attributes(dataframe.columns.tolist())
    summary_statistics = build_summary_statistics(dataframe, column_types)

    return {
        "rows": ingestion_summary["rows"],
        "columns": ingestion_summary["columns"],
        "column_types": column_types,
        "sensitive_attributes": sensitive_attributes,
        "summary_statistics": summary_statistics,
        "missing_values": ingestion_summary["missing_values"],
    }

