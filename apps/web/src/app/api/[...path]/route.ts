import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";

const DEVELOPMENT_API_ORIGIN = "http://127.0.0.1:8000";
const VPC_API_ORIGIN = "http://api:8000";
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "accept-language",
  "content-type",
  "idempotency-key",
  "x-csrf-token",
  "x-request-id",
] as const;

export function resolveApiOrigin(
  configured = process.env.INTERNAL_API_URL,
  environment = process.env.NODE_ENV,
): string | null {
  const value = configured?.trim();
  if (!value) return environment === "development" ? DEVELOPMENT_API_ORIGIN : null;
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.origin;
  } catch {
    return null;
  }
}

export function isSelfReferentialOrigin(apiOrigin: string, requestOrigin: string): boolean {
  return new URL(apiOrigin).origin === new URL(requestOrigin).origin;
}

export function isAccessRejection(response: Response): boolean {
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  return (response.status === 401 || response.status === 403) && contentType.includes("text/html");
}

function apiUnavailable(message: string) {
  return Response.json(
    { error: { code:"api_unavailable", message } },
    { status:503, headers:{ "Cache-Control":"no-store" } },
  );
}

type PrivateApiBinding = {
  fetch(input: Request): Promise<Response>;
};

async function privateApiBinding(): Promise<PrivateApiBinding|null> {
  try {
    const { env } = await getCloudflareContext({ async:true });
    const binding = (env as CloudflareEnv & { CALENDAR_API?: PrivateApiBinding }).CALENDAR_API;
    return binding ?? null;
  } catch {
    return null;
  }
}

async function proxy(request: NextRequest, context: { params: Promise<{ path:string[] }> }) {
  const vpcBinding = process.env.NODE_ENV === "development" ? null : await privateApiBinding();
  const apiOrigin = vpcBinding ? VPC_API_ORIGIN : resolveApiOrigin();
  if (!apiOrigin) {
    return apiUnavailable("事件服务尚未连接，请配置 Cloudflare VPC 或 INTERNAL_API_URL");
  }
  if (!vpcBinding && isSelfReferentialOrigin(apiOrigin, request.nextUrl.origin)) {
    return apiUnavailable("事件服务地址不能指向当前 Web Worker，请配置独立 API 地址");
  }
  const { path } = await context.params;
  const target = new URL(`/api/${path.join("/")}`, apiOrigin);
  target.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const accessClientId = process.env.CF_ACCESS_CLIENT_ID?.trim();
  const accessClientSecret = process.env.CF_ACCESS_CLIENT_SECRET?.trim();
  if (accessClientId && accessClientSecret) {
    headers.set("CF-Access-Client-Id", accessClientId);
    headers.set("CF-Access-Client-Secret", accessClientSecret);
  }
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
  const upstreamRequest = new Request(target, {
    method:request.method,
    headers,
    body,
    redirect:"manual",
  });
  let upstream: Response;
  try {
    upstream = vpcBinding
      ? await vpcBinding.fetch(upstreamRequest)
      : await fetch(upstreamRequest, { cache:"no-store" });
  } catch {
    return apiUnavailable("事件服务暂时不可达，请检查后端或 Cloudflare Tunnel");
  }
  if (isAccessRejection(upstream)) {
    return apiUnavailable("私有事件服务拒绝访问，请检查 Tunnel、VPC Service 或 Access Service Token");
  }
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
