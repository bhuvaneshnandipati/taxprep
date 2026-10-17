"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiAvailable, login, register } from "@/lib/api";

export default function AuthPage() {
  const r = useRouter();
  const [available, setAvailable] = useState(false);
  useEffect(() => setAvailable(apiAvailable()), []);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [adminCode, setAdminCode] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setErr(""); setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name, adminCode);
      r.push("/dashboard");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <main className="max-w-md mx-auto px-5 py-16">
      <h1 className="text-2xl font-bold mb-1">Prepare your 2025 tax return</h1>
      <p className="text-sm text-gray-500 mb-8">Built for international students and visa holders: residency test, Form 8843, 1040-NR with tax treaties, dual-status, plus California and New York returns.</p>
      {!available && <p className="text-sm mb-4">Hosted backend unavailable: account creation and sign-in are disabled until the replacement API is verified.</p>}
      <form className="card" onSubmit={(e) => { e.preventDefault(); if (!busy) submit(); }}>
        <div className="flex gap-2 mb-5">
          <button className={`chip ${mode === "login" ? "chip-on" : "chip-off"}`} type="button" onClick={() => setMode("login")}>Sign in</button>
          <button className={`chip ${mode === "register" ? "chip-on" : "chip-off"}`} type="button" onClick={() => setMode("register")}>Create account</button>
        </div>
        {mode === "register" && (
          <div className="mb-4"><label className="lbl" htmlFor="full-name">Full name</label>
            <input id="full-name" autoComplete="name" className="inp" value={name} onChange={(e) => setName(e.target.value)} /></div>
        )}
        <div className="mb-4"><label className="lbl" htmlFor="email">Email</label>
          <input id="email" autoComplete="email" required className="inp" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div className="mb-5"><label className="lbl" htmlFor="password">Password</label>
          <input id="password" required minLength={mode === "register" ? 8 : undefined} maxLength={128} autoComplete={mode === "register" ? "new-password" : "current-password"} className="inp" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {mode === "register" && <p className="text-xs text-gray-500 mt-1">At least 8 characters.</p>}</div>
        {mode === "register" && (
          <details className="mb-5 text-sm"><summary className="cursor-pointer text-gray-500">Administrator setup code</summary>
            <input className="inp mt-2" value={adminCode} onChange={(e) => setAdminCode(e.target.value)} placeholder="Only for the site administrator" />
          </details>)}
        {err && <p role="alert" className="text-sm text-owe mb-4">{err}</p>}
        <button className="btn w-full" type="submit" disabled={busy || !available}>
          {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
    </main>
  );
}
