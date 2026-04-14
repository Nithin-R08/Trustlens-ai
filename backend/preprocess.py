from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.config import RAW_DATA_PATH


TARGET_COLUMN = "Churn"
ID_COLUMN = "customerID"

RAW_FEATURE_COLUMNS = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
]

BASE_NUMERIC_COLUMNS = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
BASE_CATEGORICAL_COLUMNS = [column for column in RAW_FEATURE_COLUMNS if column not in BASE_NUMERIC_COLUMNS]

PHONE_DEPENDENT_COLUMN = "MultipleLines"
INTERNET_DEPENDENT_COLUMNS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]

ENGINEERED_NUMERIC_COLUMNS = [
    "AvgChargesPerMonth",
    "TenureChargeRatio",
    "ServiceCount",
    "IsMonthToMonth",
    "HasFiberOptic",
    "IsElectronicCheck",
    "AutoPay",
    "NoSupportBundle",
]

ENGINEERED_CATEGORICAL_COLUMNS = ["TenureBand", "ChargeLevel"]

MODEL_NUMERIC_COLUMNS = BASE_NUMERIC_COLUMNS + ENGINEERED_NUMERIC_COLUMNS
MODEL_CATEGORICAL_COLUMNS = BASE_CATEGORICAL_COLUMNS + ENGINEERED_CATEGORICAL_COLUMNS
MODEL_FEATURE_COLUMNS = MODEL_NUMERIC_COLUMNS + MODEL_CATEGORICAL_COLUMNS

FIELD_LABELS = {
    "gender": "Gender",
    "SeniorCitizen": "Senior Citizen",
    "Partner": "Partner",
    "Dependents": "Dependents",
    "tenure": "Tenure",
    "PhoneService": "Phone Service",
    "MultipleLines": "Multiple Lines",
    "InternetService": "Internet Service",
    "OnlineSecurity": "Online Security",
    "OnlineBackup": "Online Backup",
    "DeviceProtection": "Device Protection",
    "TechSupport": "Tech Support",
    "StreamingTV": "Streaming TV",
    "StreamingMovies": "Streaming Movies",
    "Contract": "Contract",
    "PaperlessBilling": "Paperless Billing",
    "PaymentMethod": "Payment Method",
    "MonthlyCharges": "Monthly Charges",
    "TotalCharges": "Total Charges",
}

FORM_OPTIONS = {
    "gender": ["Female", "Male"],
    "SeniorCitizen": [0, 1],
    "Partner": ["No", "Yes"],
    "Dependents": ["No", "Yes"],
    "PhoneService": ["No", "Yes"],
    "MultipleLines": ["No", "No phone service", "Yes"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "OnlineSecurity": ["No", "No internet service", "Yes"],
    "OnlineBackup": ["No", "No internet service", "Yes"],
    "DeviceProtection": ["No", "No internet service", "Yes"],
    "TechSupport": ["No", "No internet service", "Yes"],
    "StreamingTV": ["No", "No internet service", "Yes"],
    "StreamingMovies": ["No", "No internet service", "Yes"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["No", "Yes"],
    "PaymentMethod": [
        "Bank transfer (automatic)",
        "Credit card (automatic)",
        "Electronic check",
        "Mailed check",
    ],
}

DEFAULT_PROFILE = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "No",
    "Dependents": "No",
    "tenure": 12,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "Yes",
    "StreamingMovies": "Yes",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 79.5,
    "TotalCharges": None,
}


@dataclass(frozen=True)
class RiskBandThresholds:
    low: float = 0.35
    high: float = 0.65


def get_risk_band(probability: float, thresholds: RiskBandThresholds | None = None) -> str:
    thresholds = thresholds or RiskBandThresholds()
    if probability >= thresholds.high:
        return "High"
    if probability >= thresholds.low:
        return "Medium"
    return "Low"


def load_dataset(data_path=RAW_DATA_PATH) -> pd.DataFrame:
    dataframe = pd.read_csv(data_path)
    return clean_dataframe(dataframe)


def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]

    for column in RAW_FEATURE_COLUMNS:
        if column not in cleaned.columns:
            cleaned[column] = np.nan

    cleaned["TotalCharges"] = pd.to_numeric(cleaned["TotalCharges"], errors="coerce")
    cleaned["MonthlyCharges"] = pd.to_numeric(cleaned["MonthlyCharges"], errors="coerce")
    cleaned["tenure"] = pd.to_numeric(cleaned["tenure"], errors="coerce")
    cleaned["SeniorCitizen"] = pd.to_numeric(cleaned["SeniorCitizen"], errors="coerce").fillna(0).astype(int)

    for column in BASE_CATEGORICAL_COLUMNS + [TARGET_COLUMN]:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].astype("string").str.strip().fillna("")

    return cleaned


def split_features_target(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    features = dataframe[RAW_FEATURE_COLUMNS].copy()
    target = dataframe[TARGET_COLUMN].map({"Yes": 1, "No": 0}).fillna(0).astype(int)
    return features, target


def get_training_data(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return split_features_target(dataframe)


def sanitize_customer_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw_payload = payload or {}
    record = DEFAULT_PROFILE.copy()
    record.update(raw_payload)

    senior_citizen_value = record.get("SeniorCitizen", 0)
    if isinstance(senior_citizen_value, str):
        normalized = senior_citizen_value.strip().lower()
        if normalized in {"yes", "y", "true"}:
            senior_citizen_value = 1
        elif normalized in {"no", "n", "false"}:
            senior_citizen_value = 0
    record["SeniorCitizen"] = int(float(senior_citizen_value or 0))
    record["tenure"] = int(float(record.get("tenure", 0) or 0))
    record["MonthlyCharges"] = float(record.get("MonthlyCharges", 0) or 0)

    total_charges = record.get("TotalCharges")
    if total_charges in ("", None):
        total_charges = round(record["MonthlyCharges"] * max(record["tenure"], 1), 2)
    record["TotalCharges"] = float(total_charges)

    for column, options in FORM_OPTIONS.items():
        if column in record and column != "SeniorCitizen":
            value = str(record[column]).strip()
            record[column] = value if value in options else DEFAULT_PROFILE[column]

    if record["PhoneService"] == "No":
        record[PHONE_DEPENDENT_COLUMN] = "No phone service"

    if record["InternetService"] == "No":
        for column in INTERNET_DEPENDENT_COLUMNS:
            record[column] = "No internet service"

    return {column: record[column] for column in RAW_FEATURE_COLUMNS}


def prepare_inference_frame(payload: dict[str, Any] | None) -> pd.DataFrame:
    sanitized = sanitize_customer_payload(payload)
    return pd.DataFrame([sanitized], columns=RAW_FEATURE_COLUMNS)


def build_baseline_profile(dataframe: pd.DataFrame) -> dict[str, Any]:
    features, _ = split_features_target(dataframe)
    baseline: dict[str, Any] = {}

    for column in RAW_FEATURE_COLUMNS:
        if column in BASE_NUMERIC_COLUMNS:
            baseline[column] = float(pd.to_numeric(features[column], errors="coerce").median())
            if column in {"SeniorCitizen", "tenure"}:
                baseline[column] = int(round(baseline[column]))
        else:
            mode = features[column].mode(dropna=True)
            baseline[column] = str(mode.iloc[0]) if not mode.empty else DEFAULT_PROFILE[column]

    return sanitize_customer_payload(baseline)


def format_feature_value(feature_name: str, value: Any) -> str:
    if feature_name == "SeniorCitizen":
        return "Yes" if int(value) == 1 else "No"
    if feature_name == "tenure":
        return f"{int(float(value))} months"
    if feature_name in {"MonthlyCharges", "TotalCharges"}:
        return f"${float(value):.2f}"
    return str(value)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "FeatureEngineer":
        frame = clean_dataframe(pd.DataFrame(X).copy())
        charges = pd.to_numeric(frame["MonthlyCharges"], errors="coerce")
        self.monthly_charge_median_ = float(charges.median()) if not charges.dropna().empty else 0.0
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        frame = clean_dataframe(pd.DataFrame(X).copy())

        tenure = pd.to_numeric(frame["tenure"], errors="coerce").fillna(0)
        monthly = pd.to_numeric(frame["MonthlyCharges"], errors="coerce").fillna(self.monthly_charge_median_)
        total = pd.to_numeric(frame["TotalCharges"], errors="coerce")
        total = total.fillna((monthly * tenure.replace(0, 1)).round(2))

        safe_tenure = tenure.replace(0, np.nan)

        frame["AvgChargesPerMonth"] = (total / safe_tenure).replace([np.inf, -np.inf], np.nan).fillna(monthly)
        frame["TenureChargeRatio"] = (monthly / safe_tenure).replace([np.inf, -np.inf], np.nan).fillna(monthly)
        frame["ServiceCount"] = (
            frame[
                [
                    "PhoneService",
                    "MultipleLines",
                    "OnlineSecurity",
                    "OnlineBackup",
                    "DeviceProtection",
                    "TechSupport",
                    "StreamingTV",
                    "StreamingMovies",
                ]
            ]
            .isin(["Yes"])
            .sum(axis=1)
            .astype(float)
        )
        frame["IsMonthToMonth"] = frame["Contract"].eq("Month-to-month").astype(int)
        frame["HasFiberOptic"] = frame["InternetService"].eq("Fiber optic").astype(int)
        frame["IsElectronicCheck"] = frame["PaymentMethod"].eq("Electronic check").astype(int)
        frame["AutoPay"] = frame["PaymentMethod"].isin(
            ["Bank transfer (automatic)", "Credit card (automatic)"]
        ).astype(int)
        frame["NoSupportBundle"] = (
            frame["OnlineSecurity"].eq("No") & frame["TechSupport"].eq("No")
        ).astype(int)
        frame["TenureBand"] = pd.cut(
            tenure,
            bins=[-1, 12, 24, 48, 72, np.inf],
            labels=["0-12", "13-24", "25-48", "49-72", "72+"],
        ).astype("string").fillna("0-12")
        frame["ChargeLevel"] = pd.cut(
            monthly,
            bins=[-np.inf, 35, 70, 95, np.inf],
            labels=["Low", "Mid", "High", "Premium"],
        ).astype("string").fillna("Mid")

        return frame[MODEL_FEATURE_COLUMNS].copy()


def build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, MODEL_NUMERIC_COLUMNS),
            ("categorical", categorical_pipeline, MODEL_CATEGORICAL_COLUMNS),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
