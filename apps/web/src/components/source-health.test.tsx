import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SourceHealthPanel } from "./source-health";

afterEach(() => vi.unstubAllGlobals());

describe("SourceHealthPanel", () => {
  it("renders source health returned by the API instead of demo values", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok:true,
      json:async () => [
        { id:"fed", key:"fed", name:"Federal Reserve", institution:"Federal Reserve", country_code:"US", official_url:"https://example.com/fed", source_type:"html", priority:10, enabled:true, health:"healthy", schedule:"daily", consecutive_failures:0, last_success_at:"2026-09-02T04:33:45Z", last_failure_at:null, last_event_count:57 },
        { id:"bls", key:"bls", name:"U.S. BLS Release Calendar", institution:"BLS", country_code:"US", official_url:"https://example.com/bls", source_type:"ics", priority:20, enabled:true, health:"degraded", schedule:"daily", consecutive_failures:1, last_success_at:null, last_failure_at:"2026-09-02T04:07:46Z", last_event_count:null },
      ],
    }));

    render(<SourceHealthPanel />);

    expect(screen.getByText("正在读取真实来源状态…")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("U.S. BLS Release Calendar")).toBeInTheDocument());
    expect(screen.getByText("降级")).toBeInTheDocument();
    expect(screen.getByText(/失败.*12:07/)).toBeInTheDocument();
    expect(screen.getAllByText("57")).toHaveLength(2);
  });

  it("shows an unavailable state without inventing health data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok:false,
      status:503,
      json:async () => ({ error:{ message:"事件服务尚未连接" } }),
    }));

    render(<SourceHealthPanel />);

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("事件服务尚未连接"));
    expect(screen.queryByText("Federal Reserve FOMC Calendar")).not.toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(4);
  });
});
