"use client";

import { Bell, ChevronRight, Clock3, MessageSquareText } from "lucide-react";

import { labels, type CalendarEvent } from "@/lib/demo-events";
import { formatDateRange, formatEventTime } from "@/lib/date-time";

export function DailyEvents({ events, showPassed = false, onSelect, timezone = "Asia/Shanghai" }: { events: CalendarEvent[]; showPassed?: boolean; onSelect?: (event:CalendarEvent) => void; timezone?:string }) {
  const timed = events.filter((event) => event.precision === "minute");
  const tba = events.filter((event) => event.precision === "date");
  return (
    <div className="day-columns">
      <section className="panel day-list">
        <div className="panel-head"><div><h2>按时间排序</h2><p>{timed.length} 个定时事件</p></div><span className="next-pill"><Clock3 size={13} />下一个事件已标记</span></div>
        {timed.map((event, index) => (
          <article className={`day-event ${showPassed && index === 0 ? "passed" : ""} ${index === 1 ? "next" : ""}`} key={event.id}>
            <div className="day-time"><strong>{event.start ? formatEventTime(event.start, timezone) : "—"}</strong><span>{event.originalTime}</span></div>
            <i className={`impact-dot ${event.importance}`} />
            <div className="day-event-copy"><p><b>{event.country}</b>{event.institution} · {event.category}</p><h3>{event.title}</h3>{event.originalTitle && event.originalTitle !== event.title && <small>{event.originalTitle}</small>}</div>
            <div className="day-tags"><span className={`level ${event.importance}`}>{labels.importance[event.importance]}</span><span className={`status ${event.status}`}>{labels.status[event.status]}</span></div>
            <div className="row-actions"><button aria-label="个人备注"><MessageSquareText size={15} /></button><button aria-label="提醒"><Bell size={15} /></button><button aria-label={`查看 ${event.title}`} onClick={() => onSelect?.(event)}><ChevronRight size={17} /></button></div>
          </article>
        ))}
        {timed.length === 0 && <EmptyState text="当天没有定时事件；这不代表数据源抓取成功，请同时查看来源状态。" />}
      </section>
      <aside className="panel tba-panel">
        <div className="panel-head"><div><h2>时间待定</h2><p>只展示日期，不伪造具体时间</p></div></div>
        {tba.map((event) => <article className="tba-event" key={event.id}><i className={`impact-dot ${event.importance}`} /><div><h3>{event.title}</h3><p>{event.institution} · {event.country}</p><span>{formatDateRange(event.dateRangeStart ?? event.localDate, event.dateRangeEnd)} · {labels.status[event.status]}</span></div><button aria-label={`查看 ${event.title}`} onClick={() => onSelect?.(event)}><ChevronRight size={16} /></button></article>)}
        {tba.length === 0 && <EmptyState text="当天没有时间待定事件" />}
      </aside>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state"><CalendarEmptyIcon /><p>{text}</p></div>;
}

function CalendarEmptyIcon() {
  return <span aria-hidden="true">—</span>;
}
