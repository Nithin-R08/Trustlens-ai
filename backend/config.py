from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "telco_customer_churn.csv"
REFERENCE_DATA_PATH = DATA_DIR / "reference" / "telecom_data_dictionary.csv"

MODELS_DIR = PROJECT_ROOT / "models"
FIGURES_DIR = MODELS_DIR / "figures"

MODEL_PATH = MODELS_DIR / "churn_model.pkl"
EVALUATION_PATH = MODELS_DIR / "evaluation.json"
METRICS_PATH = MODELS_DIR / "metrics.json"
MODEL_COMPARISON_PATH = MODELS_DIR / "model_comparison.csv"
FEATURE_IMPORTANCE_PATH = MODELS_DIR / "feature_importance.csv"
SHAP_IMPORTANCE_PATH = MODELS_DIR / "shap_importance.csv"
CLASSIFICATION_REPORT_PATH = MODELS_DIR / "classification_report.txt"
EDA_REPORT_PATH = MODELS_DIR / "eda_report.md"

CONFUSION_MATRIX_PATH = FIGURES_DIR / "confusion_matrix.png"
CHURN_DISTRIBUTION_PATH = FIGURES_DIR / "eda_churn_distribution.png"
MONTHLY_CHARGES_PATH = FIGURES_DIR / "eda_monthly_charges_by_churn.png"
CHURN_BY_CONTRACT_PATH = FIGURES_DIR / "eda_churn_by_contract.png"
SHAP_SUMMARY_PATH = FIGURES_DIR / "shap_feature_importance.png"
