import type { ReactNode } from "react";

import { AppHeaderActions, ContextStatus } from "./app-controls";
import { Sidebar } from "./sidebar";

export function PageShell({
  active,
  eyebrow,
  title,
  summary,
  children,
}: {
  active: string;
  eyebrow: ReactNode;
  title: ReactNode;
  summary?: string;
  children: ReactNode;
}) {
  return (
    <div className="shell">
      <Sidebar active={active} />
      <main>
        <header>
          <div><small>{eyebrow}</small><h1>{title}</h1>{summary && <p className="page-summary">{summary}</p>}</div>
          <AppHeaderActions />
        </header>
        <ContextStatus />
        {children}
      </main>
    </div>
  );
}
