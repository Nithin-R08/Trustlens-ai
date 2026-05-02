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

import { analyzeDatasetLocally } from "./local-analysis";

const LOCAL_API_BASE = "http://127.0.0.1:8000";
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);
const RESULT_STORAGE_PREFIX = "trustlens-result:";

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

export function isApiConfigured() {
  return Boolean(getApiBaseUrl());
}

function rememberResult(result: TrustLensResult) {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(`${RESULT_STORAGE_PREFIX}${result.id}`, JSON.stringify(result));
}

function readRememberedResult(id: string) {
  if (typeof window === "undefined") {
    return null;
  }
  const stored = window.sessionStorage.getItem(`${RESULT_STORAGE_PREFIX}${id}`);
  return stored ? (JSON.parse(stored) as TrustLensResult) : null;
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
  if (!getApiBaseUrl()) {
    const localResult = await analyzeDatasetLocally(file);
    rememberResult(localResult);
    return localResult;
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await safeFetch(`${requireApiBaseUrl()}/analyze`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  const result = (await response.json()) as TrustLensResult;
  rememberResult(result);
  return result;
}

export async function fetchResultById(id: string): Promise<TrustLensResult> {
  if (!getApiBaseUrl()) {
    const localResult = readRememberedResult(id);
    if (localResult) {
      return localResult;
    }
    throw new Error("This browser session does not have that local analysis result. Please upload the dataset again.");
  }

  const response = await safeFetch(`${requireApiBaseUrl()}/results/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as TrustLensResult;
}

export function getReportUrl(id: string, format: "json" | "pdf") {
  const apiBaseUrl = getApiBaseUrl();
  if (apiBaseUrl) {
    return `${apiBaseUrl}/results/${id}/report?format=${format}`;
  }

  const localResult = readRememberedResult(id);
  if (!localResult || format === "pdf") {
    return "";
  }

  return `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(localResult, null, 2))}`;
}
