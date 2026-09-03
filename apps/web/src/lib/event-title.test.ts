import { describe, expect, it } from "vitest";

import type { ApiEvent } from "./api";
import { eventTitle } from "./event-title";

function event(values:Partial<ApiEvent>):ApiEvent {
  return {
    title_zh:"中文标题",
    title_original:null,
    display_title:"",
    ...values,
  } as ApiEvent;
}

describe("eventTitle", () => {
  it("uses English originals and Chinese originals directly", () => {
    expect(eventTitle(event({
      title_original:"Consumer Price Index",
      display_title:"Consumer Price Index",
    }))).toBe("Consumer Price Index");
    expect(eventTitle(event({
      title_original:"消费者物价指数",
      display_title:"消费者物价指数",
    }))).toBe("消费者物价指数");
  });

  it("uses the server-provided English translation for other languages", () => {
    expect(eventTitle(event({
      title_original:"소비자물가동향",
      display_title:"Consumer Price Index",
    }))).toBe("Consumer Price Index");
  });
});
