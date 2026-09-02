import { CalendarBoard } from "@/components/calendar-board";
import { LocalWeekLabel } from "@/components/date-labels";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { filtersFromSearchParams, type SearchParamValues } from "@/lib/filters";

export default async function WeekPage({ searchParams }:{ searchParams:Promise<SearchParamValues> }) {
  const filters = filtersFromSearchParams(await searchParams);
  return <PageShell active="/week" eyebrow={<LocalWeekLabel />} title="本周事件" summary="默认使用高密度列表，也可切换周历。"><FilterBar filters={filters} /><CalendarBoard view="week" filters={filters} /></PageShell>;
}
