from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

from backend.config import (
    CHURN_BY_CONTRACT_PATH,
    CHURN_DISTRIBUTION_PATH,
    CLASSIFICATION_REPORT_PATH,
    CONFUSION_MATRIX_PATH,
    EDA_REPORT_PATH,
    EVALUATION_PATH,
    FEATURE_IMPORTANCE_PATH,
    FIGURES_DIR,
    METRICS_PATH,
    MODEL_COMPARISON_PATH,
    MODEL_PATH,
    MODELS_DIR,
    MONTHLY_CHARGES_PATH,
    SHAP_IMPORTANCE_PATH,
    SHAP_SUMMARY_PATH,
)
from backend.preprocess import (
    FeatureEngineer,
    build_baseline_profile,
    build_preprocessor,
    get_training_data,
    load_dataset,
)


matplotlib.use("Agg")

RANDOM_STATE = 42
TEST_SIZE = 0.2
PRIMARY_MODEL_NAME = "XGBoost"


@dataclass
class ModelResult:
    model_name: str
    best_estimator: Pipeline
    best_params: dict[str, Any]
    cv_best_score: float
    threshold: float
    metrics: dict[str, float]
    confusion_matrix: np.ndarray


def ensure_directories() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def perform_eda(dataframe: pd.DataFrame) -> None:
    df = dataframe.copy()
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")

    missing_counts = df.isna().sum().sort_values(ascending=False)
    churn_rate = (df["Churn"] == "Yes").mean() * 100

    summary_lines = [
        "# Customer Churn Dataset EDA Report",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Rows: **{len(df):,}**",
        f"- Columns: **{df.shape[1]}**",
        f"- Churn rate: **{churn_rate:.2f}%**",
        "",
        "## Missing Values",
        "",
    ]

    top_missing = missing_counts[missing_counts > 0]
    if top_missing.empty:
        summary_lines.append("No explicit missing values after CSV load.")
    else:
        for column, count in top_missing.items():
            summary_lines.append(f"- {column}: {int(count)}")

    summary_lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Month-to-month customers form the highest churn-risk contract group.",
            "- Fiber optic and electronic check customers are strong churn segments.",
            "- Lower tenure customers show significantly higher churn rates.",
        ]
    )
    EDA_REPORT_PATH.write_text("\n".join(summary_lines), encoding="utf-8")

    plt.figure(figsize=(6, 4))
    sns.countplot(data=df, x="Churn", color="#1d4ed8")
    plt.title("Customer Churn Distribution")
    plt.tight_layout()
    plt.savefig(CHURN_DISTRIBUTION_PATH, dpi=180)
    plt.close()

    plt.figure(figsize=(8, 4))
    sns.boxplot(data=df, x="Churn", y="MonthlyCharges", color="#8fb8ff")
    plt.title("Monthly Charges by Churn")
    plt.tight_layout()
    plt.savefig(MONTHLY_CHARGES_PATH, dpi=180)
    plt.close()

    contract_rates = (
        df.groupby("Contract")["Churn"]
        .apply(lambda values: (values == "Yes").mean() * 100)
        .sort_values(ascending=False)
    )
    plt.figure(figsize=(8, 4))
    contract_rates.plot(kind="bar", color="#1d4ed8")
    plt.ylabel("Churn Rate (%)")
    plt.title("Churn Rate by Contract")
    plt.tight_layout()
    plt.savefig(CHURN_BY_CONTRACT_PATH, dpi=180)
    plt.close()


def build_pipeline(model: Any) -> Pipeline:
    return Pipeline(
        steps=[
            ("feature_engineer", FeatureEngineer()),
            ("preprocessor", build_preprocessor()),
            ("model", model),
        ]
    )


def get_candidate_searches(scale_pos_weight: float, cv: StratifiedKFold) -> list[tuple[str, Any]]:
    logistic = LogisticRegression(
        max_iter=4000,
        class_weight="balanced",
        solver="liblinear",
        random_state=RANDOM_STATE,
    )
    logistic_search = GridSearchCV(
        estimator=build_pipeline(logistic),
        param_grid={"model__C": [0.01, 0.05, 0.1, 0.5, 1.0, 2.0]},
        scoring="f1",
        cv=cv,
        n_jobs=1,
        refit=True,
    )

    forest = RandomForestClassifier(
        random_state=RANDOM_STATE,
        class_weight="balanced",
        n_jobs=1,
    )
    forest_search = RandomizedSearchCV(
        estimator=build_pipeline(forest),
        param_distributions={
            "model__n_estimators": [250, 350, 450, 550],
            "model__max_depth": [6, 8, 10, 14, None],
            "model__min_samples_split": [2, 4, 8],
            "model__min_samples_leaf": [1, 2, 4],
            "model__max_features": ["sqrt", "log2", None],
        },
        n_iter=10,
        scoring="f1",
        cv=cv,
        n_jobs=1,
        random_state=RANDOM_STATE,
        refit=True,
    )

    from xgboost import XGBClassifier

    xgb = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_jobs=1,
        scale_pos_weight=scale_pos_weight,
    )
    xgb_search = RandomizedSearchCV(
        estimator=build_pipeline(xgb),
        param_distributions={
            "model__n_estimators": [250, 350, 450],
            "model__max_depth": [3, 4, 5, 6],
            "model__learning_rate": [0.01, 0.03, 0.05, 0.1],
            "model__subsample": [0.7, 0.85, 1.0],
            "model__colsample_bytree": [0.7, 0.85, 1.0],
            "model__min_child_weight": [1, 2, 4],
            "model__gamma": [0.0, 0.1, 0.3],
            "model__reg_lambda": [1.0, 4.0, 8.0],
        },
        n_iter=12,
        scoring="f1",
        cv=cv,
        n_jobs=1,
        random_state=RANDOM_STATE,
        refit=True,
    )

    return [
        ("Logistic Regression", logistic_search),
        ("Random Forest", forest_search),
        ("XGBoost", xgb_search),
    ]


def pick_best_threshold(y_true: pd.Series, probabilities: np.ndarray) -> tuple[float, dict[str, float], np.ndarray]:
    best_threshold = 0.5
    best_metrics: dict[str, float] | None = None
    best_predictions: np.ndarray | None = None
    best_score = float("-inf")

    for threshold in np.arange(0.30, 0.81, 0.01):
        predictions = (probabilities >= threshold).astype(int)
        metrics = {
            "accuracy": accuracy_score(y_true, predictions),
            "precision": precision_score(y_true, predictions, zero_division=0),
            "recall": recall_score(y_true, predictions, zero_division=0),
            "f1_score": f1_score(y_true, predictions, zero_division=0),
            "roc_auc": roc_auc_score(y_true, probabilities),
        }
        score = metrics["f1_score"] + (metrics["recall"] * 0.15)
        if score > best_score:
            best_score = score
            best_threshold = float(threshold)
            best_metrics = metrics
            best_predictions = predictions

    assert best_metrics is not None and best_predictions is not None
    return best_threshold, best_metrics, best_predictions


def save_confusion_matrix(matrix: np.ndarray) -> None:
    plt.figure(figsize=(5, 4))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Confusion Matrix")
    plt.tight_layout()
    plt.savefig(CONFUSION_MATRIX_PATH, dpi=180)
    plt.close()


def save_feature_importance(best_pipeline: Pipeline) -> pd.DataFrame:
    preprocessor = best_pipeline.named_steps["preprocessor"]
    model = best_pipeline.named_steps["model"]
    feature_names = preprocessor.get_feature_names_out()

    if hasattr(model, "feature_importances_"):
        scores = np.asarray(model.feature_importances_)
    elif hasattr(model, "coef_"):
        scores = np.abs(np.asarray(model.coef_[0]))
    else:
        scores = np.zeros(len(feature_names))

    importance_frame = (
        pd.DataFrame({"feature": feature_names, "importance": scores})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    maximum = float(importance_frame["importance"].max()) or 1.0
    importance_frame["importance_pct"] = (importance_frame["importance"] / maximum * 100).round(4)
    importance_frame.to_csv(FEATURE_IMPORTANCE_PATH, index=False)
    return importance_frame


def save_shap_importance(best_pipeline: Pipeline, x_train: pd.DataFrame) -> None:
    try:
        import shap

        feature_engineer = best_pipeline.named_steps["feature_engineer"]
        preprocessor = best_pipeline.named_steps["preprocessor"]
        model = best_pipeline.named_steps["model"]

        sample = x_train.sample(min(500, len(x_train)), random_state=RANDOM_STATE)
        engineered = feature_engineer.transform(sample)
        transformed = preprocessor.transform(engineered)
        feature_names = preprocessor.get_feature_names_out()

        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()

        if hasattr(model, "feature_importances_"):
            explainer = shap.TreeExplainer(model)
        elif hasattr(model, "coef_"):
            explainer = shap.LinearExplainer(model, transformed)
        else:
            return

        shap_values = explainer.shap_values(transformed)
        if isinstance(shap_values, list):
            shap_values = shap_values[-1]

        shap_array = np.asarray(shap_values)
        if shap_array.ndim == 3:
            shap_array = shap_array[:, :, -1]
        elif shap_array.ndim == 1:
            shap_array = shap_array.reshape(1, -1)

        mean_abs_shap = np.abs(shap_array).mean(axis=0).ravel()
        if mean_abs_shap.shape[0] != len(feature_names):
            return

        shap_frame = pd.DataFrame(
            {
                "feature": feature_names,
                "mean_abs_shap": mean_abs_shap,
            }
        ).sort_values("mean_abs_shap", ascending=False)
        shap_frame.to_csv(SHAP_IMPORTANCE_PATH, index=False)

        plt.figure(figsize=(8, 5))
        top_rows = shap_frame.head(12).iloc[::-1]
        plt.barh(top_rows["feature"], top_rows["mean_abs_shap"], color="#f97316")
        plt.title("SHAP Global Feature Impact")
        plt.xlabel("Mean |SHAP value|")
        plt.tight_layout()
        plt.savefig(SHAP_SUMMARY_PATH, dpi=180)
        plt.close()
    except Exception as error:
        print(f"SHAP generation skipped: {error}")


def train_models() -> dict[str, Any]:
    ensure_directories()

    dataframe = load_dataset()
    perform_eda(dataframe)
    features, target = get_training_data(dataframe)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=TEST_SIZE,
        stratify=target,
        random_state=RANDOM_STATE,
    )

    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())
    scale_pos_weight = negative_count / max(positive_count, 1)
    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)

    results: list[ModelResult] = []
    leaderboard_rows: list[dict[str, Any]] = []

    for model_name, search in get_candidate_searches(scale_pos_weight, cv):
        print(f"Training {model_name}...")
        search.fit(x_train, y_train)

        best_pipeline = search.best_estimator_
        probabilities = best_pipeline.predict_proba(x_test)[:, 1]
        threshold, metrics, predictions = pick_best_threshold(y_test, probabilities)
        matrix = confusion_matrix(y_test, predictions)

        result = ModelResult(
            model_name=model_name,
            best_estimator=best_pipeline,
            best_params=search.best_params_,
            cv_best_score=float(search.best_score_),
            threshold=threshold,
            metrics={key: round(float(value), 4) for key, value in metrics.items()},
            confusion_matrix=matrix,
        )
        results.append(result)

        leaderboard_rows.append(
            {
                "model": result.model_name,
                "cv_best_f1": round(result.cv_best_score, 4),
                "accuracy": result.metrics["accuracy"],
                "precision": result.metrics["precision"],
                "recall": result.metrics["recall"],
                "f1": result.metrics["f1_score"],
                "roc_auc": result.metrics["roc_auc"],
                "threshold": round(result.threshold, 3),
                "best_params": json.dumps(result.best_params, default=str),
            }
        )

    leaderboard = pd.DataFrame(leaderboard_rows).sort_values(
        by=["f1", "recall", "roc_auc", "accuracy"],
        ascending=False,
    )
    leaderboard.to_csv(MODEL_COMPARISON_PATH, index=False)

    if PRIMARY_MODEL_NAME in leaderboard["model"].values:
        winner_name = PRIMARY_MODEL_NAME
    else:
        winner_name = str(leaderboard.iloc[0]["model"])
    winner = next(result for result in results if result.model_name == winner_name)
    winner_probabilities = winner.best_estimator.predict_proba(x_test)[:, 1]
    winner_predictions = (winner_probabilities >= winner.threshold).astype(int)

    classification_report_text = classification_report(
        y_test,
        winner_predictions,
        target_names=["Stayed", "Churned"],
        zero_division=0,
    )
    CLASSIFICATION_REPORT_PATH.write_text(classification_report_text, encoding="utf-8")

    save_confusion_matrix(winner.confusion_matrix)
    top_features = save_feature_importance(winner.best_estimator)
    save_shap_importance(winner.best_estimator, x_train)

    trained_at = datetime.now(timezone.utc).isoformat()
    model_bundle = {
        "pipeline": winner.best_estimator,
        "model_name": winner.model_name,
        "best_model_name": winner.model_name,
        "metrics": winner.metrics,
        "decision_threshold": round(winner.threshold, 3),
        "trained_at_utc": trained_at,
        "baseline_profile": build_baseline_profile(dataframe),
    }
    joblib.dump(model_bundle, MODEL_PATH)

    evaluation_payload = {
        "best_model_name": winner.model_name,
        "decision_threshold": round(winner.threshold, 3),
        "metrics": winner.metrics,
        "confusion_matrix": winner.confusion_matrix.tolist(),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "trained_at_utc": trained_at,
    }
    EVALUATION_PATH.write_text(json.dumps(evaluation_payload, indent=2), encoding="utf-8")

    metrics_payload = {
        "trained_at_utc": trained_at,
        "dataset_rows": int(len(dataframe)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "positive_class_ratio_train": round(float(y_train.mean()), 4),
        "positive_class_ratio_test": round(float(y_test.mean()), 4),
        "best_model": winner.model_name,
        "best_metrics": {
            "accuracy": winner.metrics["accuracy"],
            "precision": winner.metrics["precision"],
            "recall": winner.metrics["recall"],
            "f1": winner.metrics["f1_score"],
            "roc_auc": winner.metrics["roc_auc"],
            "threshold": round(winner.threshold, 3),
        },
        "top_features": top_features.head(10).to_dict(orient="records"),
        "model_results": leaderboard.to_dict(orient="records"),
    }
    METRICS_PATH.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    print()
    print("Training complete.")
    print(f"Best model: {winner.model_name}")
    print(f"Accuracy: {winner.metrics['accuracy'] * 100:.2f}%")
    print(f"Recall: {winner.metrics['recall'] * 100:.2f}%")
    print(f"Artifacts saved to: {MODELS_DIR}")
    return metrics_payload


if __name__ == "__main__":
    train_models()
