import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function engineBase() {
  return (process.env.ENGINE_URL || process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8080").replace(/\/$/, "");
}

function headers() {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const apiKey = process.env.ENGINE_API_KEY || "";
  if (apiKey) h["X-API-Key"] = apiKey;
  return h;
}

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }
  try {
    const upstream = await fetch(`${engineBase()}/v1/validation/jobs`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(body),
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Engine unreachable";
    return NextResponse.json({ detail: `Engine error: ${message}` }, { status: 502 });
  }
}
