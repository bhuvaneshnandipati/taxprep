import { NextResponse, type NextRequest } from "next/server";

// Runs on the website's server before /api/* is rewritten to the API (next.config.mjs).
// Every API call then arrives from this deployment's own address, so the API cannot see
// who the visitor is. Pass the visitor's IP along with a shared secret (PROXY_SECRET,
// server-only env on both the website and API projects) so sign-up and sign-in limits
// count each visitor separately. Headers of the same name sent by a browser are removed.
const CLIENT_IP = "x-taxprep-client-ip";
const PROXY_KEY = "x-taxprep-proxy-key";

export function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.delete(CLIENT_IP);
  headers.delete(PROXY_KEY);
  const secret = process.env.PROXY_SECRET;
  // On Vercel, x-real-ip and the single x-forwarded-for value are set by the platform.
  const ip = (request.headers.get("x-real-ip") || request.headers.get("x-forwarded-for")?.split(",").pop() || "").trim();
  if (secret && ip) {
    headers.set(CLIENT_IP, ip);
    headers.set(PROXY_KEY, secret);
  }
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: "/api/:path*" };
