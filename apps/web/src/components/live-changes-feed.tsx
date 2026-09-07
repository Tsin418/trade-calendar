"use client";

import { AlertCircle, ArrowRight, Clock3, ExternalLink, Plus, RefreshCw, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { type ApiChange, type ApiEvent, type ApiSource, fetchChanges, fetchEvent, fetchSources } from "@/lib/api";
import { formatEventDateTime } from "@/lib/date-time";
import { eventTitle } from "@/lib/event-title";
import type { FilterValues } from "@/lib/filters";
import { useLoadRetry } from "@/lib/use-load-retry";

import { usePreferences } from "./preferences-context";

type ChangeRow = { change:ApiChange; event:ApiEvent|null; source:ApiSource|null };

export function LiveChangesFeed({ filters }:{ filters:FilterValues }) {
  const { settings, readOnly, loading:preferencesLoading } = usePreferences();
  const [rows, setRows] = useState<ChangeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);
  const { attempt, retry } = useLoadRetry(Boolean(error) && !readOnly, loading);

  useEffect(() => {
    if (readOnly || preferencesLoading) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [changes, sources] = await Promise.all([fetchChanges(25), fetchSources()]);
        const uniqueIds = [...new Set(changes.map((change) => change.event_id))];
        const events = await Promise.all(uniqueIds.map(async (id) => {
          try { return await fetchEvent(id); } catch { return null; }
        }));
        if (cancelled) return;
        const eventById = new Map(uniqueIds.map((id, index) => [id, events[index]]));
        setRows(changes.map((change) => {
          const event = eventById.get(change.event_id) ?? null;
          return { change, event, source:event ? findSource(event, sources) : null };
        }));
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "变更记录加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [attempt, readOnly, preferencesLoading]);

  const filtered = useMemo(() => rows.filter((row) => matchesFilters(row, filters)), [filters, rows]);
  if (readOnly) return <div className="read-only-notice">公开链接不展示内部版本和审计记录。</div>;
  return <section className="panel change-feed" aria-busy={loading}>
    <div className="panel-head"><div><h2>变更记录</h2><p>{loading ? "正在读取…" : error ? "数据不可用" : `${filtered.length} 条符合条件`}</p></div></div>
    {error && <div className="data-error" role="alert"><AlertCircle size={16} /><span>{error}。连接恢复后将自动重试。</span><button onClick={retry} disabled={loading}>立即重试</button></div>}
    {!loading && !error && filtered.map((row) => <ChangeCard key={row.change.id} row={row} timezone={settings.timezone} />)}
    {!loading && !error && filtered.length === 0 && <div className="source-loading">暂无符合条件的真实变更记录</div>}
  </section>;
}

function ChangeCard({ row, timezone }:{ row:ChangeRow; timezone:string }) {
  const { change, event, source } = row;
  const meta = changeMeta(change.change_type);
  const diff = primaryDiff(change, timezone);
  const Icon = meta.icon;
  return <article className="change-card">
    <span className={`change-kind ${meta.tone}`}><Icon size={17} /></span>
    <div className="change-main">
      <div><h3>{meta.label}{event ? `：${eventTitle(event)}` : ""}</h3><p>{event ? `${event.institution} · ${event.country_code}` : `事件 ${change.event_id}`}{source && <a className="evidence-link" href={source.official_url} target="_blank" rel="noreferrer">官方来源 <ExternalLink size={11} /></a>}</p></div>
      <div className="diff"><span>{diff.old}</span><ArrowRight size={15} /><strong>{diff.next}</strong></div>
    </div>
    <time>{formatRelative(change.created_at)}</time>
  </article>;
}

function changeMeta(type:string) {
  if (type === "created") return { label:"新增", tone:"created", icon:Plus };
  if (type === "cancelled") return { label:"已取消", tone:"cancelled", icon:XCircle };
  if (type === "time_confirmed") return { label:"时间已确认", tone:"time", icon:Clock3 };
  if (type === "rescheduled") return { label:"已改期", tone:"rescheduled", icon:RefreshCw };
  return { label:"信息已更新", tone:"time", icon:RefreshCw } };

function primaryDiff(change:ApiChange, timezone:string):{ old:string; next:string } {
  if (change.change_type === "created") return { old:"未收录", next:"已写入真实事件库" };
  const preferred = ["starts_at", "local_date", "status", "importance", "title_zh"];
  const key = preferred.find((field) => field in change.changed_fields) ?? Object.keys(change.changed_fields)[0];
  if (!key) return { old:"—", next:"已更新" };
  const values = change.changed_fields[key];
  return { old:formatValue(key, values.old, timezone), next:formatValue(key, values.new, timezone) };
}

function formatValue(field:string, value:unknown, timezone:string):string {
  if (value === null || value === undefined || value === "") return "未设置";
  if (field === "starts_at" && typeof value === "string") return formatEventDateTime(value, timezone);
  if (typeof value === "object") return "已创建";
  return String(value);
}

function findSource(event:ApiEvent, sources:ApiSource[]):ApiSource|null {
  if (event.is_manual) return null;
  const enabled = sources.filter((source) => source.enabled && /^https?:/.test(source.official_url));
  const institution = event.institution.toLowerCase();
  return enabled.find((source) => {
    const sourceInstitution = source.institution.toLowerCase();
    return sourceInstitution.includes(institution) || institution.includes(sourceInstitution);
  }) ?? null;
}

function matchesFilters(row:ChangeRow, filters:FilterValues):boolean {
  const event = row.event;
  if (filters.market && (!event || (!event.market_tags.includes(filters.market) && event.country_code !== filters.market))) return false;
  if (filters.importance && event?.importance !== filters.importance) return false;
  if (filters.status && event?.status !== filters.status && row.change.change_type !== filters.status) return false;
  if (filters.q) {
    const haystack = `${event?.title_zh ?? ""} ${event?.title_original ?? ""} ${event?.institution ?? ""} ${JSON.stringify(row.change.changed_fields)}`.toLowerCase();
    if (!haystack.includes(filters.q.toLowerCase())) return false;
  }
  return true;
}

function formatRelative(value:string):string {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(value)) / 60_000));
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  return `${Math.round(hours / 24)} 天前`;
}
