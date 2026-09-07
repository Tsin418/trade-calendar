"use client";

import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import listPlugin from "@fullcalendar/list";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EventDrawer } from "@/components/event-drawer";
import { type ApiEvent, fetchEvents } from "@/lib/api";
import { addDays, dateKeyInTimezone, formatDateRange } from "@/lib/date-time";
import { eventTitle } from "@/lib/event-title";
import { appendFilters, type FilterValues } from "@/lib/filters";
import { useLoadRetry } from "@/lib/use-load-retry";

import { usePreferences } from "./preferences-context";

const countryAbbreviations:Record<string, string> = {
  CN:"中", JP:"日", KR:"韩", TW:"台", US:"美", HK:"港", GLOBAL:"全球",
};

export function CalendarBoard({ view, filters }: { view: "week" | "month"; filters:FilterValues }) {
  const { settings } = usePreferences();
  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [selected, setSelected] = useState<ApiEvent|null>(null);
  const [error, setError] = useState<string|null>(null);
  const [loading, setLoading] = useState(true);
  const { attempt, retry } = useLoadRetry(Boolean(error), loading);
  const [range, setRange] = useState<{ start:Date; end:Date }|null>(null);
  const initialDate = useMemo(() => dateKeyInTimezone(new Date(), settings.timezone), [settings.timezone]);
  const load = useCallback(async (start:Date, end:Date) => {
    setLoading(true);
    try {
      const query = appendFilters(new URLSearchParams({
        from:start.toISOString(), to:end.toISOString(),
        from_date:dateKeyInTimezone(start, settings.timezone),
        to_date:dateKeyInTimezone(end, settings.timezone),
        limit:"200",
      }), filters);
      const result = await fetchEvents(query.toString());
      setEvents(result.items);
      setError(null);
    } catch (reason) {
      setEvents([]);
      setError(reason instanceof Error ? reason.message : "日历数据加载失败");
    } finally {
      setLoading(false);
    }
  }, [filters, settings.timezone]);
  useEffect(() => {
    if (!range) return;
    const timer = window.setTimeout(() => void load(range.start, range.end), 0);
    return () => window.clearTimeout(timer);
  }, [load, range, attempt]);
  const calendarEvents = events.map((event) => {
    const countryCode = event.country_code.trim().toUpperCase();
    const country = countryAbbreviations[countryCode] ?? (countryCode || "未知");
    const dateRange = event.date_range_start && event.date_range_end
      ? `${formatDateRange(event.date_range_start, event.date_range_end)} · `
      : "";
    return {
      id: event.id,
      title: `${country} · ${dateRange}${eventTitle(event)}`,
      start: event.starts_at ?? event.date_range_start ?? event.local_date ?? undefined,
      end: event.starts_at
        ? event.ends_at ?? undefined
        : event.date_range_end ? addDays(event.date_range_end, 1) : undefined,
      allDay: event.date_precision === "date",
      classNames: [`fc-impact-${event.importance}`, `fc-status-${event.status}`],
    };
  });
  return (
    <>
    {error && <div className="data-error" role="alert"><span>{error}。连接恢复后将自动重试。</span><button onClick={retry} disabled={loading}>立即重试</button></div>}
    <section className="panel calendar-panel" aria-busy={loading}>
      {loading && <div className="calendar-loading">正在读取当前视图事件…</div>}
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
        initialView={view === "month" ? "dayGridMonth" : "listWeek"}
        initialDate={initialDate}
        timeZone={settings.timezone}
        firstDay={1}
        events={calendarEvents}
        headerToolbar={{ left: "prev,next today", center: "title", right: view === "month" ? "dayGridMonth,listMonth" : "listWeek,timeGridWeek" }}
        buttonText={{ today:"今天", month:"月历", week:"周历", list:"列表" }}
        locale="zh-cn"
        height="auto"
        dayMaxEvents={3}
        nowIndicator
        eventDisplay="block"
        displayEventTime
        displayEventEnd
        eventTimeFormat={{ hour:"2-digit", minute:"2-digit", hour12:false }}
        datesSet={(info) => setRange({ start:info.start, end:info.end })}
        eventClick={(info) => setSelected(events.find((event) => event.id === info.event.id) ?? null)}
      />
    </section>
    {selected && <EventDrawer event={selected} defaultDate={selected.local_date ?? selected.starts_at?.slice(0,10) ?? initialDate} onClose={() => setSelected(null)} onSaved={() => { setSelected(null); if (range) void load(range.start, range.end); }} />}
    </>
  );
}
