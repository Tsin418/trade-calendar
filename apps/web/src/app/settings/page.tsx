import { PageShell } from "@/components/page-shell";
import { SettingsForm } from "@/components/settings-form";

export default function SettingsPage() {
  return <PageShell active="/settings" eyebrow="个人配置" title="设置" summary="设置保存到真实 API；来源事实不受个性化配置影响。"><SettingsForm /></PageShell>;
}
