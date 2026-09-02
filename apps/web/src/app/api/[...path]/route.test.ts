import { describe, expect, it } from "vitest";

import { isAccessRejection, isSelfReferentialOrigin, resolveApiOrigin } from "./route";

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

  it("rejects a production API origin that points back at the same Worker", () => {
    expect(isSelfReferentialOrigin(
      "https://calendar.example.com",
      "https://calendar.example.com/api/v1/events",
    )).toBe(true);
    expect(isSelfReferentialOrigin(
      "https://api.example.com",
      "https://calendar.example.com",
    )).toBe(false);
  });

  it("recognizes Cloudflare Access HTML rejections without masking JSON API errors", () => {
    expect(isAccessRejection(new Response("forbidden", {
      status:403,
      headers:{ "content-type":"text/html; charset=UTF-8" },
    }))).toBe(true);
    expect(isAccessRejection(new Response(JSON.stringify({ error:"forbidden" }), {
      status:403,
      headers:{ "content-type":"application/json" },
    }))).toBe(false);
  });
});
