import { describe, expect, it } from "vitest";

import { resolveApiOrigin } from "./route";

describe("API proxy origin", () => {
  it("does not point a production Worker at its own loopback interface", () => {
    expect(resolveApiOrigin(undefined, "production")).toBeNull();
  });

  it("keeps the local API fallback for development", () => {
    expect(resolveApiOrigin(undefined, "development")).toBe("http://127.0.0.1:8000");
  });

  it("normalizes an explicitly configured origin", () => {
    expect(resolveApiOrigin("https://api.example.com/path", "production")).toBe("https://api.example.com");
  });

  it("rejects malformed and unsupported origins", () => {
    expect(resolveApiOrigin("not-a-url", "production")).toBeNull();
    expect(resolveApiOrigin("file:///tmp/api", "production")).toBeNull();
  });
});
