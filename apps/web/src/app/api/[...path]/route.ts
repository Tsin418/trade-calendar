import type { NextRequest } from "next/server";

const API_ORIGIN = process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ path:string[] }> }) {
  const { path } = await context.params;
  const target = new URL(`/api/${path.join("/")}`, API_ORIGIN);
  target.search = request.nextUrl.search;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
  const upstream = await fetch(target, { method:request.method, headers, body, redirect:"manual", cache:"no-store" });
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  return new Response(upstream.body, { status:upstream.status, headers:responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;

