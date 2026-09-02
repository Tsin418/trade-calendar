import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { defaultSettings, PreferencesProvider } from "@/components/preferences-context";
import Home from "./page";

vi.mock("next/navigation", () => ({
  usePathname:() => "/",
  useRouter:() => ({ push:vi.fn() }),
}));

afterEach(() => vi.unstubAllGlobals());

describe("Dashboard", () => {
  it("shows a live-data shell without hard-coded economic events", () => {
    mockLiveApi();
    render(<PreferencesProvider><Home /></PreferencesProvider>);
    expect(screen.getByRole("heading", { name: "市场总览" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "来源健康" })).toBeInTheDocument();
    expect(screen.getByText("实时数据连接")).toBeInTheDocument();
    expect(screen.queryByText("韩国 GDP 终值已改期")).not.toBeInTheDocument();
    expect(screen.queryByText("日本央行货币基础")).not.toBeInTheDocument();
  });

  it("shows every primary calendar navigation view", () => {
    mockLiveApi();
    render(<PreferencesProvider><Home /></PreferencesProvider>);
    for (const label of ["总览", "今天", "明天", "本周", "月历", "变更"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name:"今天" })).toHaveAttribute("href", "/today");
  });
});

function mockLiveApi() {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async (input:string|URL|Request) => {
    const url = String(input);
    const body = url.includes("/settings") ? defaultSettings
      : url.includes("/events") ? { items:[], total:0, limit:200, offset:0 }
      : [];
    return { ok:true, json:async () => body };
  }));
}
