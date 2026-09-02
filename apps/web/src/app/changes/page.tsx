import { FilterBar } from "@/components/filter-bar";
import { LiveChangesFeed } from "@/components/live-changes-feed";
import { PageShell } from "@/components/page-shell";
import { filtersFromSearchParams, type SearchParamValues } from "@/lib/filters";

export default async function ChangesPage({ searchParams }:{ searchParams:Promise<SearchParamValues> }) {
  const filters = filtersFromSearchParams(await searchParams);
  return <PageShell active="/changes" eyebrow="真实审计记录" title="事件变更" summary="只展示事件库中的实际版本变更；可核验来源时提供官方链接。"><FilterBar filters={filters} /><LiveChangesFeed filters={filters} /></PageShell>;
}
