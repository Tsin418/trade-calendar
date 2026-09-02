export const timezoneLabels: Record<string, string> = {
  "Asia/Shanghai":"上海时间 · UTC+8",
  "Asia/Tokyo":"东京时间 · UTC+9",
  "America/New_York":"纽约时间",
};

export function dateKeyInTimezone(value:Date, timezone:string):string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone:timezone, year:"numeric", month:"2-digit", day:"2-digit",
  }).formatToParts(value);
  const part = (type:string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function addDays(dateKey:string, days:number):string {
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

export function formatDateLabel(dateKey:string, timezone:string):string {
  const instant = zonedDateStart(dateKey, timezone);
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone:timezone, year:"numeric", month:"long", day:"numeric", weekday:"long",
  }).format(instant);
}

export function formatMonthLabel(dateKey:string, timezone:string):string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone:timezone, year:"numeric", month:"long",
  }).format(zonedDateStart(dateKey, timezone));
}

export function formatEventTime(value:string, timezone:string):string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone:timezone, hour:"2-digit", minute:"2-digit", hour12:false,
  }).format(new Date(value));
}

export function formatEventDateTime(value:string, timezone:string):string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone:timezone, month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit", hour12:false,
  }).format(new Date(value));
}

export function zonedDayRange(dateKey:string, timezone:string):{ start:Date; end:Date } {
  return { start:zonedDateStart(dateKey, timezone), end:zonedDateStart(addDays(dateKey, 1), timezone) };
}

function zonedDateStart(dateKey:string, timezone:string):Date {
  const [year, month, day] = dateKey.split("-").map(Number);
  const target = Date.UTC(year, month - 1, day);
  let guess = target;
  for (let index = 0; index < 3; index += 1) {
    const offset = timezoneOffset(new Date(guess), timezone);
    guess = target - offset;
  }
  return new Date(guess);
}

function timezoneOffset(value:Date, timezone:string):number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone:timezone,
    year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", second:"2-digit",
    hourCycle:"h23",
  }).formatToParts(value);
  const number = (type:string) => Number(parts.find((item) => item.type === type)?.value ?? 0);
  return Date.UTC(number("year"), number("month") - 1, number("day"), number("hour"), number("minute"), number("second")) - value.getTime();
}
