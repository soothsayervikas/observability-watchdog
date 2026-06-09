const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

export type HealthStatus = {
  status: string;
  environment?: string;
  security_profile?: string;
  hardening_enabled?: boolean;
  auth_required?: boolean;
};

export type HealthSummary = {
  health_score: number;
  total_logs: number;
  error_count: number;
  error_rate: number;
  open_alerts: number;
  open_critical_alerts: number;
  last_analyzed_at: string | null;
};

export type TrendPoint = {
  bucket_start: string;
  bucket_end: string;
  service: string | null;
  total_count: number;
  error_count: number;
  error_rate: number;
};

export type Alert = {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  detected_at: string;
  status: string;
};

export type WebhookDelivery = {
  id: string;
  alert_id: string;
  target_url: string;
  payload: Record<string, unknown>;
  status_code: number | null;
  success: boolean;
  attempt: number;
  error_message: string | null;
  delivered_at: string;
};

function apiHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {};
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  return { ...headers, ...extra };
}

export async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | { message?: string } };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (body.detail && typeof body.detail === "object" && body.detail.message) {
      return body.detail.message;
    }
  } catch {
    // ignore JSON parse errors
  }
  return `Request failed: ${response.status}`;
}

async function fetchJson<T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: apiHeaders(init?.headers),
    signal,
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json() as Promise<T>;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthStatus> {
  return fetchJson<HealthStatus>("/api/v1/health", undefined, signal);
}

export async function getHealthSummary(signal?: AbortSignal): Promise<HealthSummary> {
  return fetchJson<HealthSummary>("/api/v1/health/summary", undefined, signal);
}

export async function getTrends(
  service?: string,
  hours = 24,
  signal?: AbortSignal,
): Promise<{ points: TrendPoint[] }> {
  const params = new URLSearchParams({ hours: String(hours) });
  if (service) {
    params.set("service", service);
  }
  return fetchJson<{ points: TrendPoint[] }>(`/api/v1/metrics/trends?${params}`, undefined, signal);
}

export async function getAlerts(
  options?: { limit?: number; status?: string },
  signal?: AbortSignal,
): Promise<Alert[]> {
  const params = new URLSearchParams();
  if (options?.limit) {
    params.set("limit", String(options.limit));
  }
  if (options?.status) {
    params.set("status", options.status);
  }
  const query = params.toString();
  return fetchJson<Alert[]>(`/api/v1/alerts${query ? `?${query}` : ""}`, undefined, signal);
}

export async function updateAlertStatus(
  alertId: string,
  status: "ACKNOWLEDGED" | "RESOLVED",
): Promise<Alert> {
  const response = await fetch(`${API_BASE}/api/v1/alerts/${alertId}`, {
    method: "PATCH",
    headers: apiHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ status }),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json() as Promise<Alert>;
}

export async function getWebhookDeliveries(signal?: AbortSignal): Promise<WebhookDelivery[]> {
  return fetchJson<WebhookDelivery[]>("/api/v1/webhooks/deliveries", undefined, signal);
}

export type AnalyzeResult = {
  alerts_created: number;
  alerts: Alert[];
  buckets_analyzed: number;
  ai_enabled: boolean;
  ai_assessment: string | null;
  detection_method: string;
};

export type SeedResult = {
  accepted: number;
  rejected: number;
  errors: string[];
};

export async function runAnalysis(): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE}/api/v1/analyze/run`, {
    method: "POST",
    headers: apiHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json() as Promise<AnalyzeResult>;
}

export async function seedSampleData(): Promise<SeedResult> {
  const response = await fetch(`${API_BASE}/api/v1/demo/seed?dataset=error_spike`, {
    method: "POST",
    headers: apiHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json() as Promise<SeedResult>;
}

export type UploadResult = SeedResult & {
  source_file: string;
  format_detected: string;
  source_type: string;
};

export type SourceScanResult = {
  scanned_files: number;
  ingested_files: number;
  accepted_events: number;
  rejected_events: number;
  files: { filename: string; size_bytes: number; status: string }[];
  errors: string[];
};

export async function uploadLogFile(file: File, defaultService = "app-service"): Promise<UploadResult> {
  const maxMb = 100;
  if (file.size > maxMb * 1024 * 1024) {
    throw new Error(`File exceeds ${maxMb} MB limit`);
  }
  const form = new FormData();
  form.append("file", file);
  form.append("default_service", defaultService);
  const response = await fetch(`${API_BASE}/api/v1/logs/upload`, {
    method: "POST",
    headers: apiHeaders(),
    body: form,
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json() as Promise<UploadResult>;
}

export async function scanLogSources(): Promise<SourceScanResult> {
  const response = await fetch(`${API_BASE}/api/v1/sources/scan`, {
    method: "POST",
    headers: apiHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json() as Promise<SourceScanResult>;
}
