"use client";

import { BellRing, Building2, Clock3, Globe2, KeyRound, Save, Shield } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";

import { type AppSettings, rotateIcsToken, saveSettings } from "@/lib/api";

import { usePreferences } from "./preferences-context";

export function SettingsForm() {
  const preferences = usePreferences();
  if (preferences.loading) return <div className="source-loading">正在读取个人设置…</div>;
  if (preferences.error) return <div className="data-error" role="alert">{preferences.error}<button onClick={() => void preferences.reload()}>重试</button></div>;
  if (preferences.readOnly) return <div className="read-only-notice">公开链接仅供查看；个人设置和提醒请在本机版本中管理。</div>;
  return <EditableSettings initial={preferences.settings} onSaved={preferences.setSettings} />;
}

function EditableSettings({ initial, onSaved }:{ initial:AppSettings; onSaved:(settings:AppSettings)=>void }) {
  const [draft, setDraft] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ tone:"success"|"error"; text:string }|null>(null);
  const [subscriptionUrl, setSubscriptionUrl] = useState("");
  const [rotating, setRotating] = useState(false);

  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const saved = await saveSettings(draft);
      setDraft(saved);
      onSaved(saved);
      setMessage({ tone:"success", text:"设置已保存并从 API 重新读取成功" });
    } catch (reason) {
      setMessage({ tone:"error", text:reason instanceof Error ? reason.message : "设置保存失败" });
    } finally {
      setSaving(false);
    }
  }

  async function rotateToken() {
    if (!window.confirm("轮换后旧订阅地址会立即失效，确定继续吗？")) return;
    setRotating(true);
    setMessage(null);
    try {
      const result = await rotateIcsToken();
      setSubscriptionUrl(result.url);
      setMessage({ tone:"success", text:"Token 已轮换；新订阅地址仅在本页显示一次" });
    } catch (reason) {
      setMessage({ tone:"error", text:reason instanceof Error ? reason.message : "Token 轮换失败" });
    } finally {
      setRotating(false);
    }
  }

  return <form className="settings-grid" onSubmit={submit}>
    <SettingsSection icon={Globe2} title="时间与显示" description="所有事件按此时区显示，原始时区始终保留。">
      <Field label="默认时区"><select value={draft.timezone} onChange={(event) => setDraft({ ...draft, timezone:event.target.value as AppSettings["timezone"] })}><option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</option><option value="Asia/Tokyo">Asia/Tokyo (UTC+9)</option><option value="America/New_York">America/New_York</option></select></Field>
      <Field label="界面语言"><select value={draft.language} disabled><option value="zh-CN">简体中文 + 原始标题</option></select></Field>
    </SettingsSection>
    <SettingsSection icon={Building2} title="关注市场" description="影响首页优先级与默认筛选，不改变事件本身重要性。">
      <div className="chip-checks">{marketOptions.map(([code, label]) => <label key={code}><input type="checkbox" checked={draft.markets.includes(code)} onChange={(event) => setDraft({ ...draft, markets:event.target.checked ? [...draft.markets, code] : draft.markets.filter((item) => item !== code) })} />{label}</label>)}</div>
    </SettingsSection>
    <div id="reminders"><SettingsSection icon={BellRing} title="提醒规则" description="日期事件与 TBA 不产生分钟级提醒。">
      <Field label="Critical"><input value={draft.critical_lead_minutes.join(", ")} onChange={(event) => setDraft({ ...draft, critical_lead_minutes:parseMinutes(event.target.value) })} /><small>分钟前</small></Field>
      <Field label="High"><input value={draft.high_lead_minutes.join(", ")} onChange={(event) => setDraft({ ...draft, high_lead_minutes:parseMinutes(event.target.value) })} /><small>分钟前</small></Field>
      <Field label="每日摘要"><input type="time" value={draft.daily_summary.slice(0,5)} onChange={(event) => setDraft({ ...draft, daily_summary:event.target.value })} /></Field>
      <Field label="晚间预览"><input type="time" value={draft.evening_preview.slice(0,5)} onChange={(event) => setDraft({ ...draft, evening_preview:event.target.value })} /></Field>
    </SettingsSection></div>
    <SettingsSection icon={KeyRound} title="私有订阅" description="现有 Token 不回显；轮换后旧地址立即失效。">
      <Field label="订阅地址"><input readOnly value={subscriptionUrl || "出于安全考虑不回显；轮换后仅显示一次"} /></Field>
      <button className="secondary-button" type="button" disabled={rotating} onClick={() => void rotateToken()}>{rotating ? "轮换中…" : "轮换 Token"}</button>
    </SettingsSection>
    <SettingsSection icon={Shield} title="数据保留" description="事件版本长期保留，原始响应按期限清理。">
      <Field label="原始快照保留"><select value={draft.snapshot_retention_days} onChange={(event) => setDraft({ ...draft, snapshot_retention_days:Number(event.target.value) as 30|90|180 })}><option value="30">30 天</option><option value="90">90 天</option><option value="180">180 天</option></select></Field>
      <Field label="中文自动翻译"><select value={draft.auto_translation} onChange={(event) => setDraft({ ...draft, auto_translation:event.target.value as "off"|"review" })}><option value="off">关闭</option><option value="review">仅候选，人工确认</option></select></Field>
    </SettingsSection>
    <div className="settings-actions"><p><Clock3 size={14} />{message ? <span className={message.tone}>{message.text}</span> : "修改后请保存，成功结果将由 API 返回"}</p><button className="sync" disabled={saving} type="submit"><Save size={15} />{saving ? "保存中…" : "保存设置"}</button></div>
  </form>;
}

const marketOptions:Array<[AppSettings["markets"][number], string]> = [
  ["US", "美国 US"], ["JP", "日本 JP"], ["KR", "韩国 KR"], ["CN", "中国大陆 CN"], ["TW", "台湾 TW"], ["HK", "香港 HK"], ["GLOBAL", "全球 GLOBAL"],
];

function parseMinutes(value:string):number[] {
  return value.split(",").map((item) => Number(item.trim())).filter((item) => Number.isInteger(item) && item > 0 && item <= 10_080);
}

function SettingsSection({ icon:Icon, title, description, children }: { icon:typeof Globe2; title:string; description:string; children:ReactNode }) {
  return <section className="panel settings-section"><div className="settings-title"><span><Icon size={18} /></span><div><h2>{title}</h2><p>{description}</p></div></div><div className="settings-fields">{children}</div></section>;
}

function Field({ label, children }: { label:string; children:ReactNode }) {
  return <label className="settings-field"><span>{label}</span><div>{children}</div></label>;
}
