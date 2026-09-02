import { ArrowRight, Clock3, Plus, RefreshCw, XCircle } from "lucide-react";

import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";

const changes = [
  { type:"rescheduled", icon:RefreshCw, title:"韩国 GDP 终值已改期", event:"韩国 GDP 终值", old:"9 月 3 日 07:00", next:"9 月 4 日 07:00", source:"Statistics Korea", time:"28 分钟前" },
  { type:"created", icon:Plus, title:"新增：香港零售销售", event:"香港零售销售", old:"未收录", next:"9 月 3 日 16:30", source:"C&SD", time:"1 小时前" },
  { type:"time", icon:Clock3, title:"台积电月度营收时间已补充", event:"台积电月度营收", old:"时间待定", next:"9 月 10 日 13:30", source:"TSMC IR", time:"4 小时前" },
  { type:"cancelled", icon:XCircle, title:"日本内阁府记者会已取消", event:"日本内阁府记者会", old:"9 月 5 日 10:00", next:"已取消", source:"Cabinet Office", time:"昨天 18:42" },
];

export default function ChangesPage() {
  return <PageShell active="/changes" eyebrow="过去 7 天" title="事件变更" summary="新增、改期、取消与时间补充均保留旧值、新值和来源证据。"><FilterBar /><section className="panel change-feed"><div className="panel-head"><div><h2>变更记录</h2><p>{changes.length} 条需要关注</p></div></div>{changes.map(({ icon:Icon, ...item }) => <article className="change-card" key={item.title}><span className={`change-kind ${item.type}`}><Icon size={17} /></span><div className="change-main"><div><h3>{item.title}</h3><p>{item.event} · {item.source}</p></div><div className="diff"><span>{item.old}</span><ArrowRight size={15} /><strong>{item.next}</strong></div></div><time>{item.time}</time></article>)}</section></PageShell>;
}

