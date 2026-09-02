import { FilterBar } from "@/components/filter-bar";
import { LiveDailyWorkspace } from "@/components/live-daily-workspace";
import { PageShell } from "@/components/page-shell";

export default function TodayPage() {
  return <PageShell active="/today" eyebrow="2026 年 9 月 2 日 · 星期三" title="今天" summary="已发生与未发生分区显示，所有时间为上海时间。"><FilterBar /><LiveDailyWorkspace date="2026-09-02" showPassed /></PageShell>;
}
