/* All API calls go to /api on this same website; next.config.mjs forwards them to the
   backend (API_ORIGIN). The session lives in an HttpOnly cookie set by the backend, so
   no login token is ever stored where page scripts could read it. Every request sends
   X-TaxPrep: 1, which the backend requires for cookie-authenticated changes (CSRF guard). */
const BASE = "/api";
const HEADERS = { "X-TaxPrep": "1" };

export async function api(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...HEADERS, ...(opts.headers || {}) },
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/";
    throw new Error("Signed out. Please sign in again.");
  }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Error ${res.status}`);
  return res;
}
export const apiJson = async (path: string, opts: RequestInit = {}) => (await api(path, opts)).json();

async function authPost(path: string, init: RequestInit, fallback: string) {
  const res = await fetch(`${BASE}${path}`, { method: "POST", credentials: "same-origin", ...init,
    headers: { ...HEADERS, ...(init.headers || {}) } });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail;
    throw new Error(res.status === 401 ? "Incorrect email or password" : detail || `${fallback} (${res.status}). The server may be waking up — try again in 30 seconds.`);
  }
}
export async function login(email: string, password: string) {
  await authPost("/auth/login", { headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }) }, "Sign-in failed");
}
export async function register(email: string, password: string, full_name: string, admin_code = "") {
  await authPost("/auth/register", { headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name, admin_code }) }, "Registration failed");
}
export async function logout() {
  await fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "same-origin", headers: HEADERS }).catch(() => {});
  window.location.href = "/";
}
export async function deleteAccount() {
  await api("/auth/account", { method: "DELETE" });
  window.location.href = "/";
}
export async function downloadPackage(rid: number, year: number) {
  const res = await api(`/returns/${rid}/package.pdf`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `tax-return-${year}.pdf`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);   // revoking synchronously cancels the download in some browsers
}

export async function uploadDocument(rid: number, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}/returns/${rid}/documents`, {
    method: "POST", credentials: "same-origin", headers: HEADERS, body: fd,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Upload failed");
  return res.json();
}
