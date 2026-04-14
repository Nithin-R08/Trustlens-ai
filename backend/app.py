from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, render_template, request

from backend.preprocess import DEFAULT_PROFILE, FORM_OPTIONS
from backend.service import build_analytics_payload, predict_customer


app = Flask(
    __name__,
    template_folder="../frontend",
    static_folder="../frontend/static",
    static_url_path="/static",
)
app.config["JSON_SORT_KEYS"] = False


@app.get("/")
def home_page() -> str:
    return render_template("home.html", page="home")


@app.get("/predict")
@app.get("/predict-form")
def predict_page() -> str:
    return render_template("predict.html", page="predict", defaults=DEFAULT_PROFILE, form_options=FORM_OPTIONS)


@app.get("/analytics-dashboard")
def analytics_page() -> str:
    return render_template("analytics.html", page="analytics")


@app.get("/result")
def result_page() -> str:
    return render_template("result.html", page="result")


@app.get("/api/health")
def health_api() -> Any:
    try:
        payload = build_analytics_payload(force_refresh=False)
        return jsonify(
            {
                "status": "ok",
                "model": payload["model"]["name"],
                "trained_at_utc": payload["model"]["trained_at_utc"],
            }
        )
    except FileNotFoundError as error:
        return jsonify({"status": "error", "message": str(error)}), 500


@app.get("/api/form-options")
def form_options_api() -> Any:
    return jsonify({"defaults": DEFAULT_PROFILE, "options": FORM_OPTIONS})


@app.get("/api/analytics")
def analytics_api() -> Any:
    refresh = request.args.get("refresh", "false").lower() == "true"
    try:
        return jsonify(build_analytics_payload(force_refresh=refresh))
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 500
    except Exception as error:
        return jsonify({"error": f"Analytics generation failed: {error}"}), 500


@app.post("/api/predict")
def predict_api() -> Any:
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    try:
        return jsonify(predict_customer(payload))
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 500
    except Exception as error:
        return jsonify({"error": f"Prediction failed: {error}"}), 400
