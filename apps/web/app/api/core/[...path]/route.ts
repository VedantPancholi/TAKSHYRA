import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const allowed: Record<string, RegExp[]> = {
  GET: [
    /^me$/,
    /^pipelines$/,
    /^incidents$/,
    /^incidents\/[0-9a-f-]{36}$/i,
    /^incidents\/[0-9a-f-]{36}\/impact$/i,
    /^action-proposals\/[0-9a-f-]{36}$/i,
  ],
  PATCH: [/^incidents\/[0-9a-f-]{36}$/i],
  POST: [
    /^action-proposals$/,
    /^action-proposals\/[0-9a-f-]{36}\/(approve|execute)$/i,
    /^demo\/pipelines\/[0-9a-f-]{36}\/freshness-miss$/i,
  ],
};

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = (await context.params).path.join("/");
  if (!allowed[request.method]?.some((rule) => rule.test(path))) {
    return NextResponse.json(
      { error: { message: "Route unavailable" } },
      { status: 404 },
    );
  }
  const authorization = request.headers.get("authorization");
  const tenant = request.headers.get("x-tenant-slug");
  if (
    !authorization?.startsWith("Basic ") ||
    !tenant ||
    !/^[a-z0-9-]{1,50}$/.test(tenant)
  ) {
    return NextResponse.json(
      { error: { message: "Sign in and select a tenant" } },
      { status: 401 },
    );
  }
  const headers = new Headers({ authorization, "x-tenant-slug": tenant });
  const key = request.headers.get("idempotency-key");
  if (key) headers.set("idempotency-key", key);
  let body: string | undefined;
  if (request.method !== "GET") {
    if (
      request.headers.get("content-type")?.split(";")[0] !== "application/json"
    ) {
      return NextResponse.json(
        { error: { message: "JSON required" } },
        { status: 415 },
      );
    }
    body = await request.text();
    if (body.length > 8192) {
      return NextResponse.json(
        { error: { message: "Request too large" } },
        { status: 413 },
      );
    }
    headers.set("content-type", "application/json");
  }
  try {
    const upstream = await fetch(
      `${process.env.API_INTERNAL_URL ?? "http://api:8000"}/api/v1/${path}`,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        redirect: "manual",
        signal: AbortSignal.timeout(10000),
      },
    );
    const payload = await upstream.json();
    return NextResponse.json(payload, {
      status: upstream.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { error: { message: "API unavailable. Try again shortly." } },
      { status: 503 },
    );
  }
}

export { proxy as GET, proxy as PATCH, proxy as POST };
