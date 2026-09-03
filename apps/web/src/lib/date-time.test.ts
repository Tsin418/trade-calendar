import { describe, expect, it } from "vitest";

import { dateKeyInTimezone, formatDateRange, formatEventTime, zonedDayRange } from "./date-time";

describe("timezone helpers", () => {
  it("converts a September New York release into the next Shanghai date", () => {
    const event = new Date("2026-09-16T18:00:00Z");
    expect(dateKeyInTimezone(event, "Asia/Shanghai")).toBe("2026-09-17");
    expect(formatEventTime(event.toISOString(), "Asia/Shanghai")).toBe("02:00");
  });

  it("builds timezone-aware day ranges including DST", () => {
    const shanghai = zonedDayRange("2026-09-02", "Asia/Shanghai");
    expect(shanghai.start.toISOString()).toBe("2026-09-01T16:00:00.000Z");
    expect(shanghai.end.toISOString()).toBe("2026-09-02T16:00:00.000Z");

    const newYork = zonedDayRange("2026-11-01", "America/New_York");
    expect(newYork.start.toISOString()).toBe("2026-11-01T04:00:00.000Z");
    expect(newYork.end.toISOString()).toBe("2026-11-02T05:00:00.000Z");
  });

  it("formats same-month and cross-month date ranges without inventing a time", () => {
    expect(formatDateRange("2026-09-15", "2026-09-16")).toBe("9月15–16日");
    expect(formatDateRange("2027-01-31", "2027-02-01")).toBe("1月31日–2月1日");
    expect(formatDateRange("2026-09-16", null)).toBe("9月16日");
  });
});
