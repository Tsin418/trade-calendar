"use client";

import { AlertCircle, AlertTriangle, CheckCircle2, ChevronRight, Clock3, DatabaseZap, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { type ApiSource, fetchSources, type SourceHealth } from "@/lib/api";
import { useLoadRetry } from "@/lib/use-load-retry";

const healthLabels: Record<SourceHealth, string> = {
  healthy:"健康",
  stale:"待更新",
  degraded:"降级",
  failed:"失败",
  disabled:"已停用",
};

const roleLabels: Record<ApiSource["role"], string> = {
  primary:"主来源",
  secondary:"备用来源",
  discovery:"发现来源",
  internal:"内部来源",
};

const categoryLabels: Record<string,string> = {
  monetary_policy:"货币政策",
  macro_release:"宏观数据",
  market_calendar:"市场日历",
  corporate:"公司事件",
};

export function useSourceHealth() {
  const [sources, setSources] = useState<ApiSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);
  const { attempt } = useLoadRetry(Boolean(error), loading);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSources(await fetchSources());
    } catch (reason) {
      setSources([]);
      setError(reason instanceof Error ? reason.message : "来源状态加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load, attempt]);

  return { sources, loading, error, load };
}

function sourceStats(sources: ApiSource[]) {
  const enabled = sources.filter((source) => source.enabled);
  const healthy = enabled.filter((source) => source.health === "healthy").length;
  const attention = enabled.filter((source) => source.health === "stale" || source.health === "degraded").length;
  const failures = enabled.reduce((total, source) => total + source.consecutive_failures, 0);
  const events = enabled.reduce((total, source) => total + (source.last_event_count ?? 0), 0);
  const percent = enabled.length ? Math.round((healthy / enabled.length) * 100) : 0;
  return { total:enabled.length, healthy, attention, failures, events, percent };
}

export function SourceHealthPanel() {
  const { sources, loading, error, load } = useSourceHealth();
  const externalSources = useMemo(() => sources.filter((source) => !source.is_internal), [sources]);
  const stats = useMemo(() => sourceStats(externalSources), [externalSources]);
  const value = (number: number) => loading || error ? "—" : String(number);

  return <>
    {error && <div className="data-error" role="alert"><AlertCircle size={16} /><span>{error}。当前不展示推测的健康状态。</span><button onClick={() => void load()}>重试</button></div>}
    <section className="source-metrics" aria-busy={loading}>
      <Metric icon={CheckCircle2} label="健康" value={value(stats.healthy)} tone="green" />
      <Metric icon={Clock3} label="需关注" value={value(stats.attention)} tone="amber" />
      <Metric icon={AlertTriangle} label="连续失败" value={value(stats.failures)} tone="red" />
      <Metric icon={DatabaseZap} label="来源结果数" value={value(stats.events)} tone="blue" />
    </section>
    <section className="panel source-table" aria-live="polite">
      <div className="table-head"><span>来源</span><span>状态</span><span>最近结果</span><span>事件数</span><span>连续失败</span><span /></div>
      {loading && <div className="source-loading"><RefreshCw className="spin" size={15} />正在读取真实来源状态…</div>}
      {!loading && !error && externalSources.map((source) => {
        const health = source.enabled ? source.health : "disabled";
        const categories = (source.categories ?? []).map((category) => categoryLabels[category] ?? category).join("、") || "未分类";
        const expected = source.expected_items?.min === undefined && source.expected_items?.max === undefined ? "未设定" : `${source.expected_items?.min ?? 0}–${source.expected_items?.max ?? "∞"} 条`;
        return <article className="source-entry" key={source.id}>
          <div className="source-row">
            <div><b className="country-code">{source.country_code}</b><span><strong>{source.name}</strong><small>{source.institution} · {source.source_type.toUpperCase()} · {roleLabels[source.role] ?? source.role}</small></span></div>
            <span className={`source-status ${health}`}>{healthLabels[health]}</span>
            <span>{latestResult(source)}</span>
            <span>{source.last_event_count ?? "—"}</span>
            <span>{source.consecutive_failures}</span>
            <a className="source-link" href={source.official_url} target="_blank" rel="noreferrer" aria-label={`打开 ${source.name} 官方来源`}><ChevronRight size={17} /></a>
          </div>
          <div className="source-details">
            <dl><div><dt>覆盖类别</dt><dd>{categories}</dd></div><div><dt>优先级</dt><dd>{source.priority}</dd></div><div><dt>抓取计划</dt><dd>{source.schedule}</dd></div><div><dt>预期结果</dt><dd>{expected}</dd></div><div><dt>过期阈值</dt><dd>{source.stale_after_hours} 小时</dd></div><div><dt>Adapter</dt><dd>{source.adapter_available ? "已接入" : "未接入"}</dd></div></dl>
            <p><b>使用条件</b>{source.terms || "未记录"}</p>
            <p><b>兜底方案</b>{source.fallback || "无"}</p>
            {source.last_run && <p><b>最近运行</b>{runSummary(source)}</p>}
          </div>
        </article>;
      })}
      {!loading && !error && externalSources.length === 0 && <div className="source-loading">尚未注册外部数据源</div>}
    </section>
  </>;
}

export function SourceHealthSummary() {
  const { sources, loading, error, load } = useSourceHealth();
  const stats = useMemo(() => sourceStats(sources), [sources]);
  if (loading) return <div className="source-summary-state"><RefreshCw className="spin" size={14} />正在读取来源状态…</div>;
  if (error) return <div className="source-summary-state error"><AlertCircle size={14} />{error}<button onClick={() => void load()}>重试</button></div>;
  return <>
    <div className="score"><div><strong>{stats.healthy}</strong><span>/ {stats.total} 健康</span></div><b className={stats.failures ? "warning" : ""}>{stats.percent}%</b></div>
    <div className="health-bar"><i style={{ width:`${stats.percent}%` }} /></div>
    <div className="legend"><span><i />健康 {stats.healthy}</span><span><i />需关注 {stats.attention}</span><span><i />连续失败 {stats.failures}</span></div>
  </>;
}

function Metric({ icon:Icon, label, value, tone }: { icon:typeof CheckCircle2; label:string; value:string; tone:string }) {
  return <article className="source-metric"><span className={tone}><Icon size={18} /></span><div><small>{label}</small><strong>{value}</strong></div></article>;
}

function latestResult(source: ApiSource): string {
  const success = source.last_success_at ? Date.parse(source.last_success_at) : 0;
  const failure = source.last_failure_at ? Date.parse(source.last_failure_at) : 0;
  if (!success && !failure) return "尚未运行";
  const failed = failure > success;
  const value = failed ? source.last_failure_at : source.last_success_at;
  return `${failed ? "失败" : "成功"} ${formatDate(value!)}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone:"Asia/Shanghai", month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit", hour12:false,
  }).format(new Date(value));
}

function runSummary(source:ApiSource):string {
  const run = source.last_run;
  if (!run) return "尚未运行";
  if (run.status === "failed") return `${run.error_type ?? "失败"}：${run.error_message ?? "没有错误详情"}`;
  return `${run.status === "succeeded" ? "成功" : run.status} · 解析 ${run.parsed_count} · 新增 ${run.created_count} · 更新 ${run.updated_count}`;
}
