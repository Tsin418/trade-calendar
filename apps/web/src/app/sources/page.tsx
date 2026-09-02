import { AlertTriangle, CheckCircle2, ChevronRight, Clock3, DatabaseZap } from "lucide-react";

import { PageShell } from "@/components/page-shell";

const sources = [
  { name:"Federal Reserve FOMC Calendar", institution:"Federal Reserve", country:"US", type:"HTML", status:"healthy", last:"10:42", count:24, failures:0 },
  { name:"U.S. BLS Release Calendar", institution:"Bureau of Labor Statistics", country:"US", type:"ICS", status:"healthy", last:"10:31", count:113, failures:0 },
  { name:"Bank of Japan MPM", institution:"Bank of Japan", country:"JP", type:"HTML", status:"healthy", last:"09:58", count:26, failures:0 },
  { name:"Bank of Korea MPB", institution:"Bank of Korea", country:"KR", type:"HTML", status:"healthy", last:"09:47", count:16, failures:0 },
  { name:"Taiwan Advance Release Calendar", institution:"DGBAS", country:"TW", type:"HTML", status:"healthy", last:"09:31", count:87, failures:0 },
  { name:"Hong Kong Statistics Schedule", institution:"C&SD", country:"HK", type:"PDF", status:"stale", last:"昨天 07:30", count:44, failures:1 },
];

export default function SourcesPage() {
  return <PageShell active="/sources" eyebrow="11 个已注册来源" title="数据源健康" summary="抓取失败、异常空结果和字段缺失不会被展示成“没有事件”。"><section className="source-metrics"><Metric icon={CheckCircle2} label="健康" value="10" tone="green" /><Metric icon={Clock3} label="待更新" value="1" tone="amber" /><Metric icon={AlertTriangle} label="连续失败" value="0" tone="red" /><Metric icon={DatabaseZap} label="24h 观测" value="310" tone="blue" /></section><section className="panel source-table"><div className="table-head"><span>来源</span><span>状态</span><span>上次运行</span><span>事件数</span><span>连续失败</span><span /></div>{sources.map((source) => <article key={source.name}><div><b className="country-code">{source.country}</b><span><strong>{source.name}</strong><small>{source.institution} · {source.type}</small></span></div><span className={`source-status ${source.status}`}>{source.status === "healthy" ? "健康" : "待更新"}</span><span>{source.last}</span><span>{source.count}</span><span>{source.failures}</span><ChevronRight size={17} /></article>)}</section></PageShell>;
}

function Metric({ icon:Icon, label, value, tone }: { icon:typeof CheckCircle2; label:string; value:string; tone:string }) {
  return <article className="source-metric"><span className={tone}><Icon size={18} /></span><div><small>{label}</small><strong>{value}</strong></div></article>;
}

