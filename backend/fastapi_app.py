from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from backend.bias.ingestion import ingest_dataset
from backend.bias.pipeline import run_bias_pipeline
from backend.bias.profiling import profile_dataset
from backend.bias.reporting import generate_pdf_report
from backend.bias.storage import ensure_storage_dirs, load_result, load_upload, persist_result, persist_upload


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        casted = float(value)
        if np.isnan(casted) or np.isinf(casted):
            return 0.0
        return casted
    if isinstance(value, np.ndarray):
        return [sanitize_json(item) for item in value.tolist()]
    return value


app = FastAPI(
    title="TrustLens AI Bias Detection API",
    description="Upload datasets and get trust-focused bias analysis before model training.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    ensure_storage_dirs()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        dataframe, ingestion_summary = ingest_dataset(content, file.filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {error}") from error

    upload_id = str(uuid4())
    persist_upload(upload_id, file.filename, content)
    profile = profile_dataset(dataframe, ingestion_summary)

    payload = {
        "upload_id": upload_id,
        "filename": file.filename,
        "rows": ingestion_summary["rows"],
        "columns": ingestion_summary["columns"],
        "sensitive_attributes": profile["sensitive_attributes"],
        "message": "Dataset uploaded and validated successfully.",
    }
    return sanitize_json(payload)


@app.post("/analyze")
async def analyze_dataset(
    file: UploadFile | None = File(default=None),
    upload_id: str | None = Form(default=None),
) -> dict[str, Any]:
    if file is None and not upload_id:
        raise HTTPException(status_code=400, detail="Provide either a dataset file or an upload_id.")

    try:
        if file is not None:
            if not file.filename:
                raise HTTPException(status_code=400, detail="Filename is required for uploaded files.")
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            source_filename = file.filename
            source_upload_id = str(uuid4())
            persist_upload(source_upload_id, source_filename, content)
        else:
            source_upload_id = str(upload_id)
            source_filename, content = load_upload(source_upload_id)

        dataframe, ingestion_summary = ingest_dataset(content, source_filename)
        analysis = run_bias_pipeline(
            dataframe,
            dataset_name=source_filename,
            ingestion_summary=ingestion_summary,
        )
    except HTTPException:
        raise
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {error}") from error

    analysis_id = str(uuid4())
    analysis_payload = {
        "id": analysis_id,
        "upload_id": source_upload_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **analysis,
    }

    sanitized = sanitize_json(analysis_payload)
    persist_result(analysis_id, sanitized)
    return sanitized


@app.get("/results/{analysis_id}")
def get_analysis_result(analysis_id: str) -> dict[str, Any]:
    try:
        payload = load_result(analysis_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return sanitize_json(payload)


@app.get("/results/{analysis_id}/report")
def get_analysis_report(analysis_id: str, format: Literal["json", "pdf"] = "json") -> Response:
    try:
        payload = load_result(analysis_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    if format == "json":
        return JSONResponse(content=sanitize_json(payload))

    try:
        pdf_bytes = generate_pdf_report(payload)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    filename = f"trustlens-report-{analysis_id}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("backend.fastapi_app:app", host="0.0.0.0", port=8000, reload=True)

