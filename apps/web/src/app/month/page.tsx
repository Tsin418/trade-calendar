import { CalendarBoard } from "@/components/calendar-board";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";

export default function MonthPage() {
  return <PageShell active="/month" eyebrow="2026 年 9 月" title="月历" summary="单元格优先显示关键与高影响事件；时间待定事件按全天展示。"><FilterBar /><CalendarBoard view="month" /></PageShell>;
}

