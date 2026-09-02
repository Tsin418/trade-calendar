import { LocalDateLabel } from "@/components/date-labels";
import { FilterBar } from "@/components/filter-bar";
import { LiveDailyWorkspace } from "@/components/live-daily-workspace";
import { PageShell } from "@/components/page-shell";
import { filtersFromSearchParams, type SearchParamValues } from "@/lib/filters";

export default async function TomorrowPage({ searchParams }:{ searchParams:Promise<SearchParamValues> }) {
  const filters = filtersFromSearchParams(await searchParams);
  return <PageShell active="/tomorrow" eyebrow={<LocalDateLabel offsetDays={1} />} title="明天" summary="提前查看明日风险节点和交易时段安排。"><FilterBar filters={filters} /><LiveDailyWorkspace offsetDays={1} filters={filters} /></PageShell>;
}
