import { getCloudflareContext } from "@opennextjs/cloudflare";

export async function GET() {
  let readOnly = process.env.PUBLIC_READ_ONLY === "1";
  try {
    const { env } = await getCloudflareContext({ async:true });
    readOnly = (env as CloudflareEnv & { PUBLIC_READ_ONLY?:string }).PUBLIC_READ_ONLY === "1";
  } catch {
    // Local Next.js development does not provide a Cloudflare runtime context.
  }
  return Response.json(
    { readOnly },
    { headers:{ "Cache-Control":"no-store" } },
  );
}
