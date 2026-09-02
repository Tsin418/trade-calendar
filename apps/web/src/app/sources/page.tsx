import { PageShell } from "@/components/page-shell";
import { SourceHealthPanel } from "@/components/source-health";

export default function SourcesPage() {
  return <PageShell active="/sources" eyebrow="实时来源状态" title="数据源健康" summary="抓取失败、异常空结果和字段缺失不会被展示成“没有事件”。"><SourceHealthPanel /></PageShell>;
}
