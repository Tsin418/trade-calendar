import type { ApiEvent } from "./api";

export function eventTitle(event:ApiEvent):string {
  return event.display_title?.trim() || event.title_original?.trim() || event.title_zh;
}
