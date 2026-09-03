export function GET() {
  return Response.json(
    { readOnly: process.env.PUBLIC_READ_ONLY === "1" },
    { headers:{ "Cache-Control":"no-store" } },
  );
}
