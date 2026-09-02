"use client";

import { useMemo } from "react";

import { addDays, dateKeyInTimezone, formatDateLabel, formatMonthLabel } from "@/lib/date-time";

import { usePreferences } from "./preferences-context";

export function LocalDateLabel({ offsetDays = 0 }:{ offsetDays?:number }) {
  const { settings } = usePreferences();
  const label = useMemo(() => {
    const key = addDays(dateKeyInTimezone(new Date(), settings.timezone), offsetDays);
    return formatDateLabel(key, settings.timezone);
  }, [offsetDays, settings.timezone]);
  return <>{label}</>;
}

export function LocalMonthLabel() {
  const { settings } = usePreferences();
  const label = useMemo(() => formatMonthLabel(
    dateKeyInTimezone(new Date(), settings.timezone), settings.timezone,
  ), [settings.timezone]);
  return <>{label}</>;
}

export function LocalWeekLabel() {
  const { settings } = usePreferences();
  const label = useMemo(() => {
    const today = dateKeyInTimezone(new Date(), settings.timezone);
    const [year, month, day] = today.split("-").map(Number);
    const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
    const monday = addDays(today, weekday === 0 ? -6 : 1 - weekday);
    const sunday = addDays(monday, 6);
    return `${shortDate(monday)} — ${shortDate(sunday)}`;
  }, [settings.timezone]);
  return <>{label}</>;
}

function shortDate(dateKey:string):string {
  const [, month, day] = dateKey.split("-").map(Number);
  return `${month} 月 ${day} 日`;
}
