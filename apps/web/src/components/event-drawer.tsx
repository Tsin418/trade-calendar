"use client";

import { Check, LockKeyhole, Save, ShieldCheck, UnlockKeyhole, X } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";

import { type ApiEvent, fetchLocks, saveEvent, setFieldLock } from "@/lib/api";

const lockableFields = [
  ["title_zh", "中文标题"], ["starts_at", "时间"], ["importance", "重要性"], ["notes", "个人备注"],
] as const;

export function EventDrawer({ event, defaultDate, onClose, onSaved }: { event:ApiEvent|null; defaultDate:string; onClose:()=>void; onSaved:()=>void }) {
  const [precision, setPrecision] = useState<string>(event?.date_precision ?? "date");
  const [locks, setLocks] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string|null>(null);

  useEffect(() => {
    if (!event) return;
    fetchLocks(event.id).then((items) => setLocks(items.map((item) => item.field_name))).catch(() => setLocks([]));
  }, [event]);

  async function submit(formEvent:FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    setSaving(true);
    setError(null);
    const data = new FormData(formEvent.currentTarget);
    const datePrecision = String(data.get("date_precision"));
    const startsLocal = String(data.get("starts_at") ?? "");
    const payload:Record<string,unknown> = {
      title_zh:String(data.get("title_zh")),
      title_original:String(data.get("title_original") || "") || null,
      institution:String(data.get("institution")),
      country_code:String(data.get("country_code")),
      category:String(data.get("category")),
      event_type:String(data.get("event_type")),
      status:String(data.get("status")),
      importance:String(data.get("importance")),
      date_precision:datePrecision,
      local_date:datePrecision === "date" ? String(data.get("local_date")) : null,
      starts_at:datePrecision === "date" ? null : new Date(`${startsLocal}:00+08:00`).toISOString(),
      original_timezone:"Asia/Shanghai",
      original_time_text:datePrecision === "date" ? "仅日期，时间待定" : `${startsLocal} Asia/Shanghai`,
      market_tags:[String(data.get("country_code"))],
      notes:String(data.get("notes") || "") || null,
      reminder_enabled:data.get("reminder_enabled") === "on",
    };
    if (!event) payload.idempotency_key = crypto.randomUUID();
    try {
      await saveEvent(payload, event?.id);
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    } finally { setSaving(false); }
  }

  async function toggleLock(field:string) {
    if (!event) return;
    const locked = locks.includes(field);
    try {
      await setFieldLock(event.id, field, !locked);
      setLocks((current) => locked ? current.filter((item) => item !== field) : [...current, field]);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "字段锁操作失败"); }
  }

  const localStart = event?.starts_at ? toLocalInput(event.starts_at) : `${defaultDate}T09:00`;
  return <div className="drawer-backdrop" role="presentation" onMouseDown={(mouseEvent) => { if (mouseEvent.target === mouseEvent.currentTarget) onClose(); }}>
    <aside className="event-drawer" role="dialog" aria-modal="true" aria-label={event ? `编辑 ${event.title_zh}` : "人工新增事件"}>
      <div className="drawer-head"><div><span><ShieldCheck size={16} />{event ? `版本 ${event.current_version}` : "人工来源"}</span><h2>{event ? "事件详情与编辑" : "新增事件"}</h2></div><button onClick={onClose} aria-label="关闭"><X size={18} /></button></div>
      <form onSubmit={submit}>
        <div className="drawer-fields">
          <Field label="中文标题"><input name="title_zh" required defaultValue={event?.title_zh ?? ""} /></Field>
          <Field label="原标题"><input name="title_original" defaultValue={event?.title_original ?? ""} /></Field>
          <Field label="机构"><input name="institution" required defaultValue={event?.institution ?? "人工录入"} /></Field>
          <div className="field-row"><Field label="国家/地区"><input name="country_code" required maxLength={8} defaultValue={event?.country_code ?? "US"} /></Field><Field label="重要性"><select name="importance" defaultValue={event?.importance ?? "medium"}><option value="critical">关键</option><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></Field></div>
          <div className="field-row"><Field label="类别"><input name="category" required defaultValue={event?.category ?? "macro_release"} /></Field><Field label="事件类型"><input name="event_type" required defaultValue={event?.event_type ?? "activity"} /></Field></div>
          <div className="field-row"><Field label="确认状态"><select name="status" defaultValue={event?.status ?? "confirmed"}><option value="confirmed">已确认</option><option value="tba">时间待定</option><option value="expected">预计</option><option value="rescheduled">已改期</option><option value="cancelled">已取消</option><option value="completed">已完成</option></select></Field><Field label="时间精度"><select name="date_precision" value={precision} onChange={(change) => setPrecision(change.target.value)}><option value="date">仅日期</option><option value="minute">精确到分钟</option><option value="hour">精确到小时</option></select></Field></div>
          {precision === "date" ? <Field label="事件日期"><input name="local_date" type="date" required defaultValue={event?.local_date ?? defaultDate} /></Field> : <Field label="上海时间"><input name="starts_at" type="datetime-local" required defaultValue={localStart} /></Field>}
          <Field label="个人备注"><textarea name="notes" rows={4} defaultValue={event?.notes ?? ""} /></Field>
          <label className="reminder-toggle"><input type="checkbox" name="reminder_enabled" defaultChecked={event?.reminder_enabled ?? true} /><span><BellCheck />启用单事件提醒</span></label>
        </div>
        {event && <section className="field-locks"><h3>人工字段锁</h3><p>锁定后，自动来源不能覆盖该字段。</p><div>{lockableFields.map(([field,label]) => <button type="button" className={locks.includes(field) ? "locked" : ""} onClick={() => void toggleLock(field)} key={field}>{locks.includes(field) ? <LockKeyhole size={13} /> : <UnlockKeyhole size={13} />}{label}{locks.includes(field) && <Check size={12} />}</button>)}</div></section>}
        {error && <p className="drawer-error">{error}</p>}
        <footer className="drawer-footer"><button type="button" onClick={onClose}>取消</button><button className="primary" disabled={saving}><Save size={14} />{saving ? "保存中…" : "保存事件"}</button></footer>
      </form>
    </aside>
  </div>;
}

function Field({ label, children }:{ label:string; children:ReactNode }) { return <label className="drawer-field"><span>{label}</span>{children}</label>; }
function BellCheck() { return <span className="tiny-bell" aria-hidden="true">●</span>; }
function toLocalInput(value:string) { const date = new Date(value); return new Date(date.getTime() + 8*3_600_000).toISOString().slice(0,16); }
