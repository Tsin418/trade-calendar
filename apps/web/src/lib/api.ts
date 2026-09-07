export type ApiEvent = {
  id: string;
  canonical_key: string;
  title_zh: string;
  title_original: string | null;
  display_title: string;
  institution: string;
  country_code: string;
  category: string;
  event_type: string;
  status: "confirmed" | "provisional" | "tba" | "expected" | "rescheduled" | "cancelled" | "completed" | "ignored";
  importance: "critical" | "high" | "medium" | "low";
  date_precision: "minute" | "hour" | "date" | "window" | "unknown";
  starts_at: string | null;
  ends_at: string | null;
  local_date: string | null;
  date_range_start: string | null;
  date_range_end: string | null;
  original_timezone: string | null;
  original_time_text: string | null;
  reference_period: string | null;
  market_tags: string[];
  tickers: string[];
  notes: string | null;
  reminder_enabled: boolean;
  is_manual: boolean;
  current_version: number;
  last_verified_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EventListResponse = { items: ApiEvent[]; total: number; limit: number; offset: number };
export type FieldLock = { id:string; event_id:string; field_name:string; locked_by:string; reason:string|null; created_at:string };
export type ApiChange = {
  id:string;
  event_id:string;
  from_version:number|null;
  to_version:number;
  change_type:string;
  changed_fields:Record<string, { old:unknown; new:unknown }>;
  created_at:string;
};
export type SyncRun = {
  id:string;
  source_id:string;
  status:"pending"|"running"|"succeeded"|"failed"|"partial";
  created_count:number;
  updated_count:number;
  error_message:string|null;
};
export type AppSettings = {
  timezone:"Asia/Shanghai"|"Asia/Tokyo"|"America/New_York";
  language:"zh-CN";
  markets:Array<"US"|"JP"|"KR"|"CN"|"TW"|"HK"|"GLOBAL">;
  critical_lead_minutes:number[];
  high_lead_minutes:number[];
  daily_summary:string;
  evening_preview:string;
  snapshot_retention_days:30|90|180;
  auto_translation:"off"|"review";
};
export type SourceHealth = "healthy" | "stale" | "degraded" | "failed" | "disabled";
export type ApiSource = {
  id: string;
  key: string;
  name: string;
  institution: string;
  country_code: string;
  official_url: string;
  source_type: string;
  priority: number;
  enabled: boolean;
  health: SourceHealth;
  schedule: string;
  stale_after_hours: number;
  consecutive_failures: number;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_event_count: number | null;
  categories: string[];
  role: "primary" | "secondary" | "discovery" | "internal";
  expected_items: { min?:number; max?:number };
  terms: string;
  fallback: string;
  adapter_available: boolean;
  is_internal: boolean;
  last_run: {
    id:string;
    status:"pending"|"running"|"succeeded"|"failed"|"partial";
    trigger:string;
    started_at:string|null;
    finished_at:string|null;
    parsed_count:number;
    created_count:number;
    updated_count:number;
    error_type:string|null;
    error_message:string|null;
  } | null;
};

export type ApiEventSource = {
  source_id:string;
  source_key:string;
  source_name:string;
  institution:string;
  official_url:string;
  source_event_id:string|null;
  source_title:string|null;
  is_primary:boolean;
  last_verified_at:string|null;
};

export async function fetchPublicMode(): Promise<{ readOnly:boolean }> {
  const response = await readApi("/api/public-mode");
  if (!response.ok) throw new Error("无法读取访问模式，请重试");
  return response.json();
}

async function readApi(url:string):Promise<Response> {
  try {
    return await fetch(url, { cache:"no-store", signal:AbortSignal.timeout(20_000) });
  } catch (reason) {
    if (reason instanceof Error && reason.name === "TimeoutError") {
      throw new Error("数据连接超时，请稍后重试");
    }
    throw reason;
  }
}

async function apiFailureMessage(response: Response, fallback: string): Promise<string> {
  const body: unknown = await response.json().catch(() => null);
  if (body && typeof body === "object" && "error" in body) {
    const error = (body as { error?: unknown }).error;
    if (error && typeof error === "object" && "message" in error) {
      const message = (error as { message?: unknown }).message;
      if (typeof message === "string" && message.trim()) return message;
    }
  }
  return fallback;
}

export async function fetchEvents(query = ""): Promise<EventListResponse> {
  const response = await readApi(`/api/v1/events${query ? `?${query}` : ""}`);
  if (!response.ok) throw new Error(await apiFailureMessage(response, `事件 API 返回 ${response.status}`));
  return response.json();
}

export async function fetchEvent(eventId:string): Promise<ApiEvent> {
  const response = await readApi(`/api/v1/events/${eventId}`);
  if (!response.ok) throw new Error(await apiFailureMessage(response, `事件 API 返回 ${response.status}`));
  return response.json();
}

export async function fetchEventSources(eventId:string): Promise<ApiEventSource[]> {
  const response = await readApi(`/api/v1/events/${eventId}/sources`);
  if (!response.ok) throw new Error(await apiFailureMessage(response, `事件来源 API 返回 ${response.status}`));
  return response.json();
}

export async function fetchChanges(limit = 50): Promise<ApiChange[]> {
  const response = await readApi(`/api/v1/changes?limit=${limit}`);
  if (!response.ok) throw new Error(await apiFailureMessage(response, `变更 API 返回 ${response.status}`));
  return response.json();
}

export async function fetchSources(): Promise<ApiSource[]> {
  const response = await readApi("/api/v1/sources");
  if (!response.ok) throw new Error(await apiFailureMessage(response, `来源 API 返回 ${response.status}`));
  return response.json();
}

export async function syncAllSources(): Promise<SyncRun[]> {
  const response = await fetch("/api/v1/sync", {
    method:"POST",
    headers:{ "X-Request-ID":crypto.randomUUID() },
  });
  if (!response.ok) throw new Error(await apiFailureMessage(response, `同步提交失败（${response.status}）`));
  return response.json();
}

export async function fetchSettings(): Promise<AppSettings> {
  const response = await readApi("/api/v1/settings");
  if (!response.ok) throw new Error(await apiFailureMessage(response, `设置 API 返回 ${response.status}`));
  return response.json();
}

export async function saveSettings(payload:AppSettings): Promise<AppSettings> {
  const response = await fetch("/api/v1/settings", {
    method:"PUT",
    headers:{ "Content-Type":"application/json", "X-Request-ID":crypto.randomUUID() },
    body:JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await apiFailureMessage(response, `设置保存失败（${response.status}）`));
  return response.json();
}

export async function rotateIcsToken(): Promise<{ token:string; url:string }> {
  const response = await fetch("/api/v1/ics-token/rotate", {
    method:"POST",
    headers:{ "X-Request-ID":crypto.randomUUID() },
  });
  if (!response.ok) throw new Error(await apiFailureMessage(response, `Token 轮换失败（${response.status}）`));
  return response.json();
}

export async function saveEvent(payload: Record<string, unknown>, eventId?: string): Promise<ApiEvent> {
  const response = await fetch(eventId ? `/api/v1/events/${eventId}` : "/api/v1/events", {
    method: eventId ? "PATCH" : "POST",
    headers: { "Content-Type":"application/json", "X-Request-ID":crypto.randomUUID() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await apiFailureMessage(response, `保存失败（${response.status}）`));
  }
  return response.json();
}

export async function fetchLocks(eventId:string): Promise<FieldLock[]> {
  const response = await readApi(`/api/v1/events/${eventId}/locks`);
  if (!response.ok) throw new Error("无法读取字段锁");
  return response.json();
}

export async function setFieldLock(eventId:string, field:string, locked:boolean): Promise<void> {
  const response = await fetch(`/api/v1/events/${eventId}/locks/${field}`, {
    method: locked ? "PUT" : "DELETE",
    headers: { "Content-Type":"application/json", "X-Request-ID":crypto.randomUUID() },
    body: locked ? JSON.stringify({ reason:"从 Web 界面人工锁定" }) : undefined,
  });
  if (!response.ok && response.status !== 204) throw new Error("字段锁操作失败");
}
