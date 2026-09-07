import { describe, expect, it } from "vitest";

import type { ApiEvent } from "./api";
import { displayText, eventTitle } from "./event-title";

function event(values:Partial<ApiEvent>):ApiEvent {
  return {
    title_zh:"中文标题",
    title_original:null,
    display_title:"",
    ...values,
  } as ApiEvent;
}

describe("eventTitle", () => {
  it("never falls back to untranslated Korean in a legacy Chinese field", () => {
    expect(eventTitle(event({
      title_original:"한국 통계 발표", title_zh:"韩国统计发布：한국 통계 발표",
      display_title:"韩国统计发布：한국 통계 발표",
    }))).toBe("标题翻译中");
    expect(displayText("ㅎㅏㄴ" )).toBe("翻译中");
  });
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
