import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import type { ApiEvent } from "@/lib/api";
import { needsTranslation } from "@/lib/event-title";
import { EventDrawer } from "./event-drawer";

vi.mock("./preferences-context", () => ({ usePreferences:() => ({ readOnly:true }) }));
afterEach(() => vi.unstubAllGlobals());

it("shows cached Chinese translations while preserving source text outside visible fields", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok:true, json:async () => [{
    source_id:"korea", source_name:"Official schedule", source_title:"한국 통계 발표",
    display_title:"韩国统计公告", is_primary:true, official_url:"https://example.com",
  }] }));
  const event = {
    id:"korea-event", title_original:"한국 통계 발표", title_zh:"韩国统计发布：한국 통계 발표",
    display_title:"韩国统计公告", institution:"한국 통계 기관",
    display_institution:"韩国统计机构", local_date:"2026-09-07", date_precision:"date",
    country_code:"KR", category:"macro_release", event_type:"activity", current_version:1,
    status:"confirmed", importance:"low",
  } as ApiEvent;
  const { container } = render(<EventDrawer event={event} defaultDate="2026-09-07" onClose={() => {}} onSaved={() => {}} />);
  await waitFor(() => expect(screen.getByText("韩国统计公告")).toBeInTheDocument());
  expect(needsTranslation(container.textContent)).toBe(false);
  for (const input of screen.getAllByRole("textbox")) {
    expect(needsTranslation((input as HTMLInputElement).value)).toBe(false);
  }
  expect(container.querySelector('input[name="title_original"]')).toHaveAttribute("type", "hidden");
  expect(container.querySelector('input[name="title_original"]')).toHaveValue("한국 통계 발표");
});
