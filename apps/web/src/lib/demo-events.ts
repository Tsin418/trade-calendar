export type CalendarEvent = {
  id: string;
  title: string;
  originalTitle: string;
  institution: string;
  country: string;
  market: string;
  category: string;
  importance: "critical" | "high" | "medium" | "low";
  status: "confirmed" | "tba" | "expected" | "rescheduled" | "cancelled" | "ignored";
  precision: "minute" | "date";
  start?: string;
  localDate?: string;
  dateRangeStart?: string;
  dateRangeEnd?: string;
  originalTime?: string;
  source: string;
};

export const labels = {
  importance: { critical:"关键", high:"高", medium:"中", low:"低" },
  status: { confirmed:"已确认", tba:"时间待定", expected:"预计", rescheduled:"已改期", cancelled:"已取消", ignored:"已忽略" },
};
