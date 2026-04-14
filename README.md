# TrustLens AI

Dataset Bias Detection and Trust Framework

## Structure

```text
trustlens ai/
|-- backend/         # FastAPI backend (upload, analyze, results)
|-- frontend/        # Next.js React frontend (landing, upload, results)
`-- requirements.txt # Python dependencies
```

## Backend (FastAPI)

1. Install Python dependencies:

```powershell
cd "C:\Users\Nithin R\OneDrive\Documents\New project\trustlens ai"
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Start API server:

```powershell
..\.venv\Scripts\python.exe -m uvicorn backend.fastapi_app:app --reload --host 0.0.0.0 --port 8000
```

Endpoints:

- `POST /upload`
- `POST /analyze`
- `GET /results/{id}`
- `GET /results/{id}/report?format=json|pdf`

## Frontend (Next.js + Tailwind)

1. Install dependencies:

```powershell
cd "C:\Users\Nithin R\OneDrive\Documents\New project\trustlens ai\frontend"
npm install
```

2. Run frontend:

```powershell
npm run dev
```

3. Open:

- `http://localhost:3000`

If backend runs on a different URL:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
```

## Spline Hero

- Uses `@splinetool/react-spline` with iframe fallback
- Scene URL: `https://my.spline.design/unchained-WgbTDe9RnAlSWiXPchrvW3eg/`
