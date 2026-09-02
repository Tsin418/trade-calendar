import { CalendarBoard } from "@/components/calendar-board";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";

export default function WeekPage() {
  return <PageShell active="/week" eyebrow="9 月 1 日 — 9 月 7 日" title="本周事件" summary="默认使用高密度列表，也可切换周历。"><FilterBar /><CalendarBoard view="week" /></PageShell>;
}

