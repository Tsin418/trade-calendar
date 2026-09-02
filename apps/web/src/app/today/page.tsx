import { LocalDateLabel } from "@/components/date-labels";
import { FilterBar } from "@/components/filter-bar";
import { LiveDailyWorkspace } from "@/components/live-daily-workspace";
import { PageShell } from "@/components/page-shell";
import { filtersFromSearchParams, type SearchParamValues } from "@/lib/filters";

export default async function TodayPage({ searchParams }:{ searchParams:Promise<SearchParamValues> }) {
  const filters = filtersFromSearchParams(await searchParams);
  return <PageShell active="/today" eyebrow={<LocalDateLabel />} title="今天" summary="已发生与未发生分区显示，时间按个人设置转换，原始时区同时保留。"><FilterBar filters={filters} /><LiveDailyWorkspace filters={filters} showPassed /></PageShell>;
}
