import { NextResponse, type NextRequest } from "next/server";
import { MIRROR_ORIGIN, injectPatchScript } from "../../../lib/mirror";

export const dynamic = "force-dynamic";

function buildTargetUrl(request: NextRequest, segments: string[]) {
  const pathname = `/${segments.join("/")}`;
  const target = new URL(pathname, MIRROR_ORIGIN);
  target.search = request.nextUrl.search;
  return target;
}

function copyUpstreamHeaders(headers: Headers) {
  const copied = new Headers(headers);
  copied.delete("content-length");
  copied.delete("content-encoding");
  copied.delete("transfer-encoding");
  copied.delete("content-security-policy");
  copied.delete("content-security-policy-report-only");
  return copied;
}

async function proxyGet(request: NextRequest, segments: string[]) {
  const target = buildTargetUrl(request, segments);
  const upstream = await fetch(target.toString(), {
    method: "GET",
    headers: {
      accept: request.headers.get("accept") ?? "*/*",
      "accept-language": request.headers.get("accept-language") ?? "en-US,en;q=0.9",
      "user-agent": request.headers.get("user-agent") ?? "Mozilla/5.0"
    },
    redirect: "manual",
    cache: "no-store"
  });

  const contentType = upstream.headers.get("content-type") ?? "";
  const headers = copyUpstreamHeaders(upstream.headers);

  if (contentType.includes("text/html")) {
    const html = await upstream.text();
    return new NextResponse(injectPatchScript(html), {
      status: upstream.status,
      headers
    });
  }

  const body = await upstream.arrayBuffer();
  return new NextResponse(body, {
    status: upstream.status,
    headers
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path = [] } = await context.params;
  return proxyGet(request, path);
}

export async function HEAD(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path = [] } = await context.params;
  const target = buildTargetUrl(request, path);

  const upstream = await fetch(target.toString(), {
    method: "HEAD",
    headers: {
      accept: request.headers.get("accept") ?? "*/*",
      "accept-language": request.headers.get("accept-language") ?? "en-US,en;q=0.9",
      "user-agent": request.headers.get("user-agent") ?? "Mozilla/5.0"
    },
    redirect: "manual",
    cache: "no-store"
  });

  return new NextResponse(null, {
    status: upstream.status,
    headers: copyUpstreamHeaders(upstream.headers)
  });
}
