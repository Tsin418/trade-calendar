import { Bell, Globe2, RefreshCw, Search } from "lucide-react";
import type { ReactNode } from "react";

import { Sidebar } from "./sidebar";

export function PageShell({
  active,
  eyebrow,
  title,
  summary,
  children,
}: {
  active: string;
  eyebrow: string;
  title: string;
  summary?: string;
  children: ReactNode;
}) {
  return (
    <div className="shell">
      <Sidebar active={active} />
      <main>
        <header>
          <div><small>{eyebrow}</small><h1>{title}</h1>{summary && <p className="page-summary">{summary}</p>}</div>
          <div className="actions">
            <button className="search"><Search size={17} />搜索事件 <kbd>⌘ K</kbd></button>
            <button className="bell" aria-label="通知"><Bell size={18} /><i /></button>
            <button className="sync"><RefreshCw size={16} />立即同步</button>
          </div>
        </header>
        <div className="context"><span><Globe2 size={15} />上海时间 · UTC+8</span><p>实时连接与抓取状态以数据源页为准</p></div>
        {children}
      </main>
    </div>
  );
}
