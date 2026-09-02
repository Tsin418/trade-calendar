import { FilterBar } from "@/components/filter-bar";
import { LiveDailyWorkspace } from "@/components/live-daily-workspace";
import { PageShell } from "@/components/page-shell";

export default function TomorrowPage() {
  return <PageShell active="/tomorrow" eyebrow="2026 年 9 月 3 日 · 星期四" title="明天" summary="提前查看明日风险节点和交易时段安排。"><FilterBar /><LiveDailyWorkspace date="2026-09-03" /></PageShell>;
}
