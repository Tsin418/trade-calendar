import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Dashboard", () => {
  it("shows the next critical event and source health", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "FOMC 利率决议" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "来源健康" })).toBeInTheDocument();
    expect(screen.getByText("实时数据连接")).toBeInTheDocument();
  });

  it("shows every primary calendar navigation view", () => {
    render(<Home />);
    for (const label of ["总览", "今天", "明天", "本周", "月历", "变更"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
