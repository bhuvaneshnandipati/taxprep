const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export function apiAvailable(): boolean {
  if (typeof window === "undefined") return false;
  const local = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  try {
    const target = new URL(BASE);
    if (target.hostname === "render.com" || target.hostname.endsWith(".onrender.com")) return false;
    return local || (process.env.NEXT_PUBLIC_ENABLE_API === "true" && target.protocol === "https:");
  } catch { return false; }
}
function requireApi() {
  if (!apiAvailable()) throw new Error("The hosted backend is not available. This preview does not accept taxpayer information.");
}

export function token(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("taxprep_token");
}
export function setToken(t: string) { localStorage.setItem("taxprep_token", t); }
export function clearToken() { localStorage.removeItem("taxprep_token"); }

export async function api(path: string, opts: RequestInit = {}) {
  requireApi();
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
      ...(opts.headers || {}),
    },
  });
  if (res.status === 401 && typeof window !== "undefined") {
    clearToken();
    window.location.href = "/";
    throw new Error("Session expired");
  }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Error ${res.status}`);
  return res;
}
export const apiJson = async (path: string, opts: RequestInit = {}) => (await api(path, opts)).json();

export async function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password });
  requireApi();
  const res = await fetch(`${BASE}/auth/login`, { method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
  if (!res.ok) throw new Error(res.status === 401 ? "Incorrect email or password" : `Sign-in failed (${res.status}). The server may be waking up — try again in 30 seconds.`);
  setToken((await res.json()).access_token);
}
export async function register(email: string, password: string, full_name: string, admin_code = "") {
  requireApi();
  const res = await fetch(`${BASE}/auth/register`, { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name, admin_code }) });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Registration failed");
  setToken((await res.json()).access_token);
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
  requireApi();
  const res = await fetch(`${BASE}/returns/${rid}/documents`, {
    method: "POST",
    headers: token() ? { Authorization: `Bearer ${token()}` } : {},
    body: fd,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Upload failed");
  return res.json();
}
