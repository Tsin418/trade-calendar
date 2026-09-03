"use client";

import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { type AppSettings, fetchPublicMode, fetchSettings } from "@/lib/api";

export const defaultSettings:AppSettings = {
  timezone:"Asia/Shanghai",
  language:"zh-CN",
  markets:["US", "JP", "KR", "TW", "HK", "GLOBAL"],
  critical_lead_minutes:[120, 60, 15],
  high_lead_minutes:[60, 15],
  daily_summary:"07:30:00",
  evening_preview:"20:30:00",
  snapshot_retention_days:90,
  auto_translation:"off",
};

type PreferencesValue = {
  settings:AppSettings;
  loading:boolean;
  error:string|null;
  readOnly:boolean;
  setSettings:(settings:AppSettings)=>void;
  reload:()=>Promise<void>;
};

const PreferencesContext = createContext<PreferencesValue|undefined>(undefined);

export function PreferencesProvider({ children }:{ children:ReactNode }) {
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string|null>(null);
  const [readOnly, setReadOnly] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const mode = await fetchPublicMode();
      setReadOnly(mode.readOnly);
      if (mode.readOnly) {
        setSettings(defaultSettings);
        return;
      }
      setSettings(await fetchSettings());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "设置读取失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, []);
  const value = useMemo(
    () => ({ settings, loading, error, readOnly, setSettings, reload }),
    [settings, loading, error, readOnly],
  );
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences():PreferencesValue {
  const value = useContext(PreferencesContext);
  if (!value) throw new Error("usePreferences must be used inside PreferencesProvider");
  return value;
}
