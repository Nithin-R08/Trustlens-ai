from __future__ import annotations

import io
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.bias.constants import SUPPORTED_UPLOAD_EXTENSIONS


def _clean_column_name(name: str) -> str:
    normalized = re.sub(r"\s+", "_", str(name).strip().lower())
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return normalized or "column"


def _ensure_unique_column_names(columns: list[str]) -> list[str]:
    name_counter: Counter[str] = Counter()
    unique: list[str] = []
    for column in columns:
        base = column
        name_counter[base] += 1
        if name_counter[base] == 1:
            unique.append(base)
        else:
            unique.append(f"{base}_{name_counter[base]}")
    return unique


def _read_csv(content: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(content))


def _read_excel(content: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content), engine="openpyxl")


def read_uploaded_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))
        raise ValueError(f"Unsupported file format '{suffix}'. Supported formats: {supported}")

    if suffix == ".csv":
        dataframe = _read_csv(content)
    else:
        dataframe = _read_excel(content)

    if dataframe.empty:
        raise ValueError("Uploaded dataset is empty.")

    cleaned_columns = [_clean_column_name(column) for column in dataframe.columns.tolist()]
    dataframe.columns = _ensure_unique_column_names(cleaned_columns)
    return dataframe


def validate_dataframe_schema(dataframe: pd.DataFrame) -> None:
    if dataframe.shape[0] < 10:
        raise ValueError("Dataset should contain at least 10 rows for reliable bias analysis.")
    if dataframe.shape[1] < 2:
        raise ValueError("Dataset should contain at least 2 columns for analysis.")

    fully_missing = [column for column in dataframe.columns if dataframe[column].isna().all()]
    if fully_missing:
        raise ValueError(
            "Dataset contains fully empty columns that cannot be analyzed: "
            + ", ".join(fully_missing[:8])
        )


def normalize_missing_values(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = dataframe.copy()

    missing_counts = frame.isna().sum().to_dict()
    missing_percentages = ((frame.isna().mean() * 100).round(2)).to_dict()

    numeric_columns = frame.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = [column for column in frame.columns if column not in numeric_columns]

    imputations: dict[str, Any] = {}

    for column in numeric_columns:
        series = pd.to_numeric(frame[column], errors="coerce")
        if series.isna().all():
            frame[column] = 0.0
            imputations[column] = {"strategy": "constant_zero", "value": 0.0}
            continue
        median_value = float(series.median())
        frame[column] = series.fillna(median_value)
        imputations[column] = {"strategy": "median", "value": round(median_value, 6)}

    for column in categorical_columns:
        series = frame[column].astype("string").fillna(pd.NA)
        mode_values = series.mode(dropna=True)
        fill_value = "unknown" if mode_values.empty else str(mode_values.iloc[0])
        frame[column] = series.fillna(fill_value).astype(str)
        imputations[column] = {"strategy": "mode", "value": fill_value}

    missing_report = {
        "missing_counts": missing_counts,
        "missing_percentages": missing_percentages,
        "imputation_strategies": imputations,
    }
    return frame, missing_report


def ingest_dataset(content: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataframe = read_uploaded_dataframe(content, filename)
    validate_dataframe_schema(dataframe)
    cleaned, missing_report = normalize_missing_values(dataframe)
    ingestion_summary = {
        "rows": int(cleaned.shape[0]),
        "columns": int(cleaned.shape[1]),
        "column_names": cleaned.columns.tolist(),
        "missing_values": missing_report,
    }
    return cleaned, ingestion_summary

