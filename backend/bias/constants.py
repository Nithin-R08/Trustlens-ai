from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
UPLOADS_DIR = ARTIFACTS_DIR / "uploads"
RESULTS_DIR = ARTIFACTS_DIR / "bias_results"

SUPPORTED_UPLOAD_EXTENSIONS = {".csv", ".xls", ".xlsx"}

SENSITIVE_ATTRIBUTE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "gender": ("gender", "sex"),
    "age": ("age", "dob", "birth"),
    "income": ("income", "salary", "wage", "earning"),
    "region": ("region", "location", "state", "city", "country", "zipcode", "zip"),
    "caste": ("caste", "ethnicity", "race", "community"),
}

TARGET_COLUMN_CANDIDATES = (
    "target",
    "label",
    "outcome",
    "class",
    "approved",
    "default",
    "churn",
    "fraud",
    "hired",
    "selected",
    "status",
)

EXPLAINABILITY_PROMPT = (
    "You are an AI fairness expert. Analyze the dataset summary and explain bias risks, "
    "affected groups, and how to fix them."
)

