import { BellRing, Building2, Clock3, Globe2, KeyRound, Save, Shield } from "lucide-react";
import type { ReactNode } from "react";

import { PageShell } from "@/components/page-shell";

export default function SettingsPage() {
  return <PageShell active="/settings" eyebrow="个人配置" title="设置" summary="个性化配置不会改变来源事实；人工覆盖会形成审计记录。"><form className="settings-grid"><SettingsSection icon={Globe2} title="时间与显示" description="所有事件按此时区显示，原始时区始终保留。"><Field label="默认时区"><select defaultValue="Asia/Shanghai"><option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</option><option value="Asia/Tokyo">Asia/Tokyo (UTC+9)</option><option value="America/New_York">America/New_York</option></select></Field><Field label="界面语言"><select defaultValue="zh-CN"><option value="zh-CN">简体中文 + 原始标题</option></select></Field></SettingsSection><SettingsSection icon={Building2} title="关注市场" description="影响首页优先级与默认筛选，不改变事件本身重要性。"><div className="chip-checks">{["美国 US","日本 JP","韩国 KR","台湾 TW","香港 HK","全球 GLOBAL"].map((item) => <label key={item}><input type="checkbox" defaultChecked />{item}</label>)}</div></SettingsSection><SettingsSection icon={BellRing} title="提醒规则" description="日期事件与 TBA 不产生分钟级提醒。"><Field label="Critical"><input defaultValue="120, 60, 15" /><small>分钟前</small></Field><Field label="High"><input defaultValue="60, 15" /><small>分钟前</small></Field><Field label="每日摘要"><input type="time" defaultValue="07:30" /></Field><Field label="晚间预览"><input type="time" defaultValue="20:30" /></Field></SettingsSection><SettingsSection icon={KeyRound} title="私有订阅" description="ICS Token 泄露后可轮换；旧地址将立即失效。"><Field label="订阅地址"><input readOnly value="https://calendar.example.com/calendar/••••••••.ics" /></Field><button className="secondary-button" type="button">轮换 Token</button></SettingsSection><SettingsSection icon={Shield} title="数据保留" description="事件版本长期保留，原始响应按期限清理。"><Field label="原始快照保留"><select defaultValue="90"><option value="30">30 天</option><option value="90">90 天</option><option value="180">180 天</option></select></Field><Field label="中文自动翻译"><select defaultValue="off"><option value="off">关闭</option><option value="review">仅候选，人工确认</option></select></Field></SettingsSection><div className="settings-actions"><p><Clock3 size={14} />上次保存：尚未连接 API</p><button className="sync" type="submit"><Save size={15} />保存设置</button></div></form></PageShell>;
}

function SettingsSection({ icon:Icon, title, description, children }: { icon:typeof Globe2; title:string; description:string; children:ReactNode }) {
  return <section className="panel settings-section"><div className="settings-title"><span><Icon size={18} /></span><div><h2>{title}</h2><p>{description}</p></div></div><div className="settings-fields">{children}</div></section>;
}

function Field({ label, children }: { label:string; children:ReactNode }) {
  return <label className="settings-field"><span>{label}</span><div>{children}</div></label>;
}
