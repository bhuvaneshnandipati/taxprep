const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function token(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("taxprep_token");
}
export function setToken(t: string) { localStorage.setItem("taxprep_token", t); }
export function clearToken() { localStorage.removeItem("taxprep_token"); }

export async function api(path: string, opts: RequestInit = {}) {
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
  const res = await fetch(`${BASE}/auth/login`, { method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
  if (!res.ok) throw new Error("Incorrect email or password");
  setToken((await res.json()).access_token);
}
export async function register(email: string, password: string, full_name: string) {
  const res = await fetch(`${BASE}/auth/register`, { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name }) });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Registration failed");
  setToken((await res.json()).access_token);
}
export async function downloadPackage(rid: number, year: number) {
  const res = await api(`/returns/${rid}/package.pdf`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `filing-package-${year}.pdf`; a.click();
  URL.revokeObjectURL(url);
}

export async function uploadDocument(rid: number, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/returns/${rid}/documents`, {
    method: "POST",
    headers: token() ? { Authorization: `Bearer ${token()}` } : {},
    body: fd,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Upload failed");
  return res.json();
}
