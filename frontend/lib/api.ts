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

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE;
}

async function parseError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

export async function analyzeDataset(file: File): Promise<TrustLensResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${getApiBaseUrl()}/analyze`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as TrustLensResult;
}

export async function fetchResultById(id: string): Promise<TrustLensResult> {
  const response = await fetch(`${getApiBaseUrl()}/results/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as TrustLensResult;
}

export function getReportUrl(id: string, format: "json" | "pdf") {
  return `${getApiBaseUrl()}/results/${id}/report?format=${format}`;
}

