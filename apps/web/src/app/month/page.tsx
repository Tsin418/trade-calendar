import { CalendarBoard } from "@/components/calendar-board";
import { LocalMonthLabel } from "@/components/date-labels";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { filtersFromSearchParams, type SearchParamValues } from "@/lib/filters";

export default async function MonthPage({ searchParams }:{ searchParams:Promise<SearchParamValues> }) {
  const filters = filtersFromSearchParams(await searchParams);
  return <PageShell active="/month" eyebrow={<LocalMonthLabel />} title="月历" summary="单元格优先显示关键与高影响事件；时间待定事件按全天展示。"><FilterBar filters={filters} /><CalendarBoard view="month" filters={filters} /></PageShell>;
}
