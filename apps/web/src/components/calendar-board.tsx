"use client";

import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import listPlugin from "@fullcalendar/list";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { useCallback, useEffect, useState } from "react";

import { EventDrawer } from "@/components/event-drawer";
import { type ApiEvent, fetchEvents } from "@/lib/api";
import { labels } from "@/lib/demo-events";

export function CalendarBoard({ view }: { view: "week" | "month" }) {
  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [selected, setSelected] = useState<ApiEvent|null>(null);
  const [error, setError] = useState<string|null>(null);
  const load = useCallback(async () => {
    try {
      const result = await fetchEvents(new URLSearchParams({
        from:"2026-08-01T00:00:00Z", to:"2026-12-01T00:00:00Z", limit:"200",
      }).toString());
      setEvents(result.items);
      setError(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "日历数据加载失败"); }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  const calendarEvents = events.map((event) => ({
    id: event.id,
    title: `${labels.importance[event.importance]} · ${event.title_zh}`,
    start: event.starts_at ?? event.local_date ?? undefined,
    allDay: event.date_precision === "date",
    classNames: [`fc-impact-${event.importance}`, `fc-status-${event.status}`],
  }));
  return (
    <>
    {error && <div className="data-error">{error}。请同时检查 Sources 页面。</div>}
    <section className="panel calendar-panel">
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
        initialView={view === "month" ? "dayGridMonth" : "listWeek"}
        initialDate="2026-09-02"
        events={calendarEvents}
        headerToolbar={{ left: "prev,next today", center: "title", right: view === "month" ? "dayGridMonth,listMonth" : "listWeek,timeGridWeek" }}
        buttonText={{ today:"今天", month:"月历", week:"周历", list:"列表" }}
        locale="zh-cn"
        height="auto"
        dayMaxEvents={3}
        nowIndicator
        eventDisplay="block"
        eventClick={(info) => setSelected(events.find((event) => event.id === info.event.id) ?? null)}
      />
    </section>
    {selected && <EventDrawer event={selected} defaultDate={selected.local_date ?? selected.starts_at?.slice(0,10) ?? "2026-09-02"} onClose={() => setSelected(null)} onSaved={() => { setSelected(null); void load(); }} />}
    </>
  );
}
