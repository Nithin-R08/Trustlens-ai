# TrustLens AI Vercel Deployment

This project is now ready for a Vercel frontend deployment.

## Recommended Setup

Deploy the Next.js frontend on Vercel and deploy the FastAPI backend as a separate public API service.

Vercel frontend settings:

- Project root directory: `frontend`
- Install command: `npm install`
- Build command: `npm run build`
- Output directory: leave empty / use Vercel default for Next.js
- Environment variable: `NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com`

Important: `NEXT_PUBLIC_API_BASE_URL` must be a live backend URL. Do not use `localhost` on Vercel.

## Backend Hosting

The FastAPI backend can run on Render, Railway, Fly.io, Azure, AWS, or another API host.

Use the lighter production dependency file for API hosting:

```bash
pip install -r requirements-api.txt
```

Start command:

```bash
uvicorn backend.fastapi_app:app --host 0.0.0.0 --port 8000
```

Health check endpoint:

```text
/health
```

## Vercel Environment Variables

Add these in Vercel Project Settings > Environment Variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com
NEXT_PUBLIC_ENABLE_SPLINE_RUNTIME=0
```

Optional backend LLM variables, set these on the backend host, not in the frontend:

```text
MISTRAL_API_KEY=your_key_here
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_MODEL=mistral-large-latest
```

## Local Commands

Frontend:

```powershell
Set-Location "C:\Users\Nithin R\OneDrive\Desktop\trustleans ai\frontend"
npm.cmd run dev
```

Backend:

```powershell
Set-Location "C:\Users\Nithin R\OneDrive\Desktop\trustleans ai"
& ".\.venv\Scripts\python.exe" -m uvicorn backend.fastapi_app:app --reload --host 127.0.0.1 --port 8000
```

## Why The Backend URL Matters

When the site is hosted on Vercel, the browser cannot call `127.0.0.1:8000` because that points to the visitor's own computer. The frontend now shows a clear configuration error if the production API URL is missing.
