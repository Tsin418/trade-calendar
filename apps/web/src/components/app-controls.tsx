"use client";

import { Bell, Globe2, RefreshCw, Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { fetchSources, syncAllSources } from "@/lib/api";
import { timezoneLabels } from "@/lib/date-time";

import { usePreferences } from "./preferences-context";

export function AppHeaderActions() {
  const { readOnly } = usePreferences();
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState<{ tone:"success"|"error"; text:string }|null>(null);

  useEffect(() => {
    const shortcut = (event:KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);

  async function sync() {
    setSyncing(true);
    setNotice(null);
    try {
      const runs = await syncAllSources();
      setNotice({ tone:"success", text:`已提交 ${runs.length} 个来源同步任务` });
    } catch (reason) {
      setNotice({ tone:"error", text:reason instanceof Error ? reason.message : "同步提交失败" });
    } finally {
      setSyncing(false);
    }
  }

  function submitSearch(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = String(new FormData(event.currentTarget).get("q") ?? "").trim();
    if (!query) return;
    setSearchOpen(false);
    router.push(`/week?q=${encodeURIComponent(query)}`);
  }

  return <>
    <div className="actions">
      <button className="search" onClick={() => setSearchOpen(true)}><Search size={17} />搜索事件 <kbd>Ctrl K</kbd></button>
      {readOnly ? <span className="public-mode-badge"><Globe2 size={14} />公开只读</span> : <>
        <button className="bell" aria-label="提醒设置" onClick={() => router.push("/settings#reminders")}><Bell size={18} /></button>
        <button className="sync" disabled={syncing} onClick={() => void sync()}><RefreshCw className={syncing ? "spin" : ""} size={16} />{syncing ? "提交中…" : "立即同步"}</button>
      </>}
    </div>
    {notice && <div className={`action-toast ${notice.tone}`} role={notice.tone === "error" ? "alert" : "status"}>{notice.text}<button aria-label="关闭提示" onClick={() => setNotice(null)}><X size={14} /></button></div>}
    {searchOpen && <div className="search-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSearchOpen(false); }}>
      <form className="search-dialog" role="dialog" aria-modal="true" aria-label="搜索事件" onSubmit={submitSearch}>
        <Search size={18} /><input name="q" aria-label="搜索关键词" placeholder="输入标题、机构、代码或备注" autoFocus /><button type="submit">搜索</button><button type="button" aria-label="关闭搜索" onClick={() => setSearchOpen(false)}><X size={17} /></button>
      </form>
    </div>}
  </>;
}

export function ContextStatus() {
  const { settings } = usePreferences();
  const [status, setStatus] = useState("正在检查数据连接…");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    fetchSources().then((sources) => {
      if (cancelled) return;
      const enabled = sources.filter((source) => source.enabled);
      const healthy = enabled.filter((source) => source.health === "healthy").length;
      setStatus(`${healthy}/${enabled.length} 个来源健康`);
      setFailed(healthy !== enabled.length);
    }).catch((reason) => {
      if (cancelled) return;
      setStatus(reason instanceof Error ? reason.message : "数据连接不可用");
      setFailed(true);
    });
    return () => { cancelled = true; };
  }, []);
  return <div className={`context ${failed ? "context-error" : ""}`}><span><Globe2 size={15} />{timezoneLabels[settings.timezone] ?? settings.timezone}</span><p>{status}</p></div>;
}
