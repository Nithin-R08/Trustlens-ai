from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from backend.bias.constants import RESULTS_DIR, UPLOADS_DIR


def _safe_name(filename: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    return sanitized or "dataset"


def ensure_storage_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def persist_upload(upload_id: str, filename: str, content: bytes) -> dict[str, str]:
    ensure_storage_dirs()
    safe_filename = _safe_name(filename)
    stored_path = UPLOADS_DIR / f"{upload_id}__{safe_filename}"
    meta_path = UPLOADS_DIR / f"{upload_id}.json"

    stored_path.write_bytes(content)
    metadata = {
        "upload_id": upload_id,
        "original_filename": filename,
        "stored_filename": stored_path.name,
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def load_upload(upload_id: str) -> tuple[str, bytes]:
    meta_path = UPLOADS_DIR / f"{upload_id}.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Upload ID '{upload_id}' was not found.")

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    stored_filename = metadata.get("stored_filename")
    if not stored_filename:
        raise FileNotFoundError(f"Upload metadata for '{upload_id}' is invalid.")

    stored_path = UPLOADS_DIR / stored_filename
    if not stored_path.exists():
        raise FileNotFoundError(f"Uploaded file for '{upload_id}' no longer exists.")

    return metadata.get("original_filename", stored_filename), stored_path.read_bytes()


def persist_result(analysis_id: str, payload: dict[str, Any]) -> Path:
    ensure_storage_dirs()
    result_path = RESULTS_DIR / f"{analysis_id}.json"
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return result_path


def load_result(analysis_id: str) -> dict[str, Any]:
    result_path = RESULTS_DIR / f"{analysis_id}.json"
    if not result_path.exists():
        raise FileNotFoundError(f"Analysis result '{analysis_id}' was not found.")
    return json.loads(result_path.read_text(encoding="utf-8"))

