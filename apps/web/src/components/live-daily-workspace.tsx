"use client";

import { AlertCircle, Plus, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DailyEvents } from "@/components/daily-events";
import { type ApiEvent, fetchEvents } from "@/lib/api";
import type { CalendarEvent } from "@/lib/demo-events";

import { EventDrawer } from "./event-drawer";

export function LiveDailyWorkspace({ date, showPassed = false }: { date:string; showPassed?:boolean }) {
  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [selected, setSelected] = useState<ApiEvent | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const start = new Date(`${date}T00:00:00+08:00`);
    const end = new Date(start.getTime() + 86_400_000);
    try {
      const result = await fetchEvents(new URLSearchParams({
        from:start.toISOString(), to:end.toISOString(), limit:"200",
      }).toString());
      setEvents(result.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "事件数据加载失败");
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const calendarEvents = useMemo(() => events.map(toCalendarEvent), [events]);
  function select(event:CalendarEvent) {
    setSelected(events.find((item) => item.id === event.id) ?? null);
  }

  return <>
    <div className="live-toolbar">
      <div>{loading ? <><RefreshCw className="spin" size={14} />正在读取事件…</> : <>API 实时数据 · {events.length} 条</>}</div>
      <button onClick={() => setCreating(true)}><Plus size={14} />人工新增事件</button>
    </div>
    {error && <div className="data-error"><AlertCircle size={16} /><span>{error}。来源失败不等于当天没有事件。</span><button onClick={() => void load()}>重试</button><X size={14} /></div>}
    <DailyEvents events={calendarEvents} showPassed={showPassed} onSelect={select} />
    {(selected || creating) && <EventDrawer
      event={creating ? null : selected}
      defaultDate={date}
      onClose={() => { setSelected(null); setCreating(false); }}
      onSaved={() => { setSelected(null); setCreating(false); void load(); }}
    />}
  </>;
}

export function toCalendarEvent(event:ApiEvent): CalendarEvent {
  const precision = event.date_precision === "date" || !event.starts_at ? "date" : "minute";
  return {
    id:event.id,
    title:event.title_zh,
    originalTitle:event.title_original ?? event.title_zh,
    institution:event.institution,
    country:event.country_code,
    market:event.market_tags[0] ?? event.country_code,
    category:event.category,
    importance:event.importance,
    status:event.status === "provisional" || event.status === "completed" ? "confirmed" : event.status,
    precision,
    start:event.starts_at ?? undefined,
    localDate:event.local_date ?? undefined,
    originalTime:event.original_time_text ?? undefined,
    source:event.is_manual ? "人工来源" : event.institution,
  };
}
