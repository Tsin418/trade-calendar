import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContextStatus } from "./app-controls";
import { DashboardWorkspace } from "./dashboard-workspace";
import { defaultSettings, PreferencesProvider } from "./preferences-context";
import { SourceHealthSummary } from "./source-health";

vi.mock("next/navigation", () => ({ useRouter:() => ({ push:vi.fn() }) }));

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function tick(milliseconds = 1) {
  await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds); });
  // Loads scheduled by a React effect after the retry need their own turn.
  await act(async () => { await vi.advanceTimersByTimeAsync(1); });
}

describe("connection recovery", () => {
  it("recovers dashboard events and the header after repeated 503s without refreshing", async () => {
    let unavailable = true;
    const fetchMock = vi.fn(async (input:string) => {
      if (input === "/api/public-mode") return Response.json({ readOnly:true });
      if (input.includes("/settings")) return Response.json(defaultSettings);
      if (unavailable) return Response.json({ error:{ message:"事件服务暂时不可达" } }, { status:503 });
      if (input.includes("/sources")) return Response.json([{ enabled:true, health:"healthy", consecutive_failures:0 }]);
      if (input.includes("/events")) return Response.json({
        items:input.includes("importance=critical") ? [] : [{
          id:"recovered", title_zh:"恢复后的真实事件", title_original:null,
          institution:"恢复测试来源", country_code:"JP", market_tags:[], importance:"low",
          date_precision:"date", local_date:"2026-09-07", starts_at:null, status:"confirmed",
        }], total:1,
      });
      return Response.json([]);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PreferencesProvider><ContextStatus /><DashboardWorkspace /></PreferencesProvider>);
    await tick();
    expect(screen.getByRole("alert")).toHaveTextContent("事件服务暂时不可达");
    expect(screen.queryByText("恢复后的真实事件")).not.toBeInTheDocument();

    const firstAttempts = fetchMock.mock.calls.length;
    await tick(15_000);
    expect(fetchMock.mock.calls.length).toBeGreaterThan(firstAttempts);
    expect(screen.getByRole("alert")).toHaveTextContent("事件服务暂时不可达");

    unavailable = false;
    await tick(15_000);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name:"恢复后的真实事件" })).toBeInTheDocument();
    expect(screen.getByText("1/1 个来源健康")).toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([url]) => !url.includes("/sync"))).toBe(true);
    const recoveredAttempts = fetchMock.mock.calls.length;
    await tick(60_000);
    expect(fetchMock).toHaveBeenCalledTimes(recoveredAttempts);
  });

  it("waits while offline, retries once on reconnect, and cleans up after unmount", async () => {
    const online = vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = render(<SourceHealthSummary />);
    await tick();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await tick(30_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    online.mockReturnValue(true);
    act(() => {
      window.dispatchEvent(new Event("online"));
      window.dispatchEvent(new Event("focus"));
    });
    await tick();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    unmount();
    act(() => window.dispatchEvent(new Event("focus")));
    await tick(30_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not overlap an in-flight recovery request", async () => {
    let finishRequest!:(response:Response) => void;
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockImplementation(() => new Promise<Response>((resolve) => { finishRequest = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SourceHealthSummary />);
    await tick();
    await tick(15_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    act(() => window.dispatchEvent(new Event("focus")));
    await tick(30_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await act(async () => { finishRequest(Response.json([])); });
    expect(screen.queryByText("Failed to fetch")).not.toBeInTheDocument();
  });
});
