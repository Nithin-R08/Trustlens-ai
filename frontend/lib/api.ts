export type TrustLensMetrics = {
  demographic_parity_difference: number;
  disparate_impact_ratio: number;
  statistical_parity: number;
  representation_imbalance_score: number;
  class_balance_ratio?: number;
  proxy_feature_count?: number;
};

export type TrustLensResult = {
  id: string;
  upload_id?: string;
  created_at_utc?: string;
  dataset_name: string;
  bias_risk: "High" | "Medium" | "Low";
  trust_score: number;
  sensitive_attributes: string[];
  metrics: TrustLensMetrics;
  insights: string;
  recommendations: string[];
  details?: Record<string, unknown>;
};

const LOCAL_API_BASE = "http://127.0.0.1:8000";
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "");
}

function isLocalBrowserHost() {
  if (typeof window === "undefined") {
    return false;
  }
  return LOCAL_HOSTNAMES.has(window.location.hostname);
}

export function getApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) {
    return trimTrailingSlash(configured);
  }

  if (process.env.NODE_ENV !== "production" || isLocalBrowserHost()) {
    return LOCAL_API_BASE;
  }

  return "";
}

function requireApiBaseUrl() {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    throw new Error(
      "Backend API URL is not configured. In Vercel, add NEXT_PUBLIC_API_BASE_URL with your deployed FastAPI backend URL, then redeploy."
    );
  }
  return apiBaseUrl;
}

async function parseError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

async function safeFetch(input: RequestInfo | URL, init?: RequestInit) {
  try {
    return await fetch(input, init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Could not reach the TrustLens backend API. Check that NEXT_PUBLIC_API_BASE_URL points to a live FastAPI server and that CORS is enabled."
      );
    }
    throw error;
  }
}

export async function analyzeDataset(file: File): Promise<TrustLensResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await safeFetch(`${requireApiBaseUrl()}/analyze`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as TrustLensResult;
}

export async function fetchResultById(id: string): Promise<TrustLensResult> {
  const response = await safeFetch(`${requireApiBaseUrl()}/results/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as TrustLensResult;
}

export function getReportUrl(id: string, format: "json" | "pdf") {
  return `${requireApiBaseUrl()}/results/${id}/report?format=${format}`;
}
