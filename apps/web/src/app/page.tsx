import { DashboardWorkspace } from "@/components/dashboard-workspace";
import { LocalDateLabel } from "@/components/date-labels";
import { PageShell } from "@/components/page-shell";

export default function Home() {
  return <PageShell active="/" eyebrow={<LocalDateLabel />} title="市场总览" summary="事件、变更和来源健康均来自实时 API；连接失败时不展示演示数据。"><DashboardWorkspace /></PageShell>;
}
