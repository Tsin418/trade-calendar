import {
  Activity,
  CalendarDays,
  Clock3,
  FileClock,
  Gauge,
  LayoutDashboard,
  ListFilter,
  Settings,
} from "lucide-react";
import Link from "next/link";

const nav = [
  { label: "总览", href: "/", icon: LayoutDashboard },
  { label: "今天", href: "/today", icon: Clock3 },
  { label: "明天", href: "/tomorrow", icon: CalendarDays },
  { label: "本周", href: "/week", icon: ListFilter },
  { label: "月历", href: "/month", icon: CalendarDays },
  { label: "变更", href: "/changes", icon: FileClock },
];

export function Sidebar({ active = "/" }: { active?: string }) {
  return (
    <aside className="sidebar">
      <Link className="brand" href="/">
        <span><Activity size={19} /></span>
        <div><strong>交易日历</strong><small>MARKET PULSE</small></div>
      </Link>
      <nav aria-label="主导航">
        <p>工作台</p>
        {nav.map(({ label, href, icon: Icon }) => (
          <Link href={href} aria-label={label} className={active === href ? "active" : ""} key={href}>
            <Icon size={18} /><b>{label}</b>
          </Link>
        ))}
        <p className="system-label">系统</p>
        <Link aria-label="数据源" className={active === "/sources" ? "active" : ""} href="/sources">
          <Gauge size={18} /><b>数据源</b><i />
        </Link>
        <Link aria-label="设置" className={active === "/settings" ? "active" : ""} href="/settings">
          <Settings size={18} /><b>设置</b>
        </Link>
      </nav>
      <div className="system-ok"><Activity size={18} /><div><strong>实时数据连接</strong><small>状态见数据源页</small></div></div>
    </aside>
  );
}
