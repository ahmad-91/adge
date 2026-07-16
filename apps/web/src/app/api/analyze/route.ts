import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const engineUrl = (process.env.ENGINE_URL || process.env.NEXT_PUBLIC_ENGINE_URL || "http://127.0.0.1:8080").replace(/\/$/, "");
  const apiKey = process.env.ENGINE_API_KEY || "";

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (apiKey) headers["X-API-Key"] = apiKey;

  try {
    const upstream = await fetch(`${engineUrl}/v1/analyze`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Engine unreachable";
    return NextResponse.json(
      { detail: `Engine error: ${message}` },
      { status: 502 }
    );
  }
}
