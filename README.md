# TrustLens AI

Dataset Bias Detection and Trust Framework.

TrustLens AI lets users upload CSV or Excel datasets, profiles sensitive attributes, detects bias risks before model training, computes fairness metrics, and returns a trust score with explainable recommendations.

## Project Structure

```text
trustleans ai/
|-- backend/              # FastAPI backend: upload, analyze, results, reports
|-- frontend/             # Next.js frontend: landing, upload, results
|-- requirements.txt      # Full Python dependencies
|-- requirements-api.txt  # Lean API hosting dependencies
|-- vercel.json           # Root Vercel fallback config
`-- VERCEL_DEPLOYMENT.md  # Vercel deployment guide
```

## Local Frontend

PowerShell:

```powershell
Set-Location "C:\Users\Nithin R\OneDrive\Desktop\trustleans ai\frontend"
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:3000
```

## Local Backend

PowerShell:

```powershell
Set-Location "C:\Users\Nithin R\OneDrive\Desktop\trustleans ai"
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-api.txt
& ".\.venv\Scripts\python.exe" -m uvicorn backend.fastapi_app:app --reload --host 127.0.0.1 --port 8000
```

API endpoints:

- `GET /health`
- `POST /upload`
- `POST /analyze`
- `GET /results/{id}`
- `GET /results/{id}/report?format=json|pdf`

## Vercel Frontend Deployment

Recommended Vercel project settings:

- Root directory: `frontend`
- Install command: `npm install`
- Build command: `npm run build`
- Output directory: leave blank / use Vercel default

Add this Vercel environment variable:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-deployed-fastapi-backend.com
```

Do not use `localhost` or `127.0.0.1` in Vercel. The backend must be deployed publicly first.

See `VERCEL_DEPLOYMENT.md` for the full deployment checklist.

## Spline Hero

The landing page uses the reliable Spline iframe fallback by default:

```text
https://my.spline.design/unchained-WgbTDe9RnAlSWiXPchrvW3eg/
```

If you want to enable the Spline React runtime later, set:

```text
NEXT_PUBLIC_ENABLE_SPLINE_RUNTIME=1
```

For Vercel, keep it disabled unless you specifically need runtime interactions.
