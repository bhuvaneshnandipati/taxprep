"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";

export default function AuthPage() {
  const r = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setErr(""); setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name);
      r.push("/dashboard");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <main className="max-w-md mx-auto px-5 py-16">
      <h1 className="text-2xl font-bold mb-1">Prepare your 2025 tax return</h1>
      <p className="text-sm text-gray-500 mb-8">Federal 1040 / 1040-NR and California 540 / 540NR. Every visa status supported.</p>
      <div className="card">
        <div className="flex gap-2 mb-5">
          <button className={`chip ${mode === "login" ? "chip-on" : "chip-off"}`} onClick={() => setMode("login")}>Sign in</button>
          <button className={`chip ${mode === "register" ? "chip-on" : "chip-off"}`} onClick={() => setMode("register")}>Create account</button>
        </div>
        {mode === "register" && (
          <div className="mb-4"><label className="lbl">Full name</label>
            <input className="inp" value={name} onChange={(e) => setName(e.target.value)} /></div>
        )}
        <div className="mb-4"><label className="lbl">Email</label>
          <input className="inp" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div className="mb-5"><label className="lbl">Password</label>
          <input className="inp" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && submit()} />
          {mode === "register" && <p className="text-xs text-gray-500 mt-1">At least 8 characters.</p>}</div>
        {err && <p className="text-sm text-owe mb-4">{err}</p>}
        <button className="btn w-full" onClick={submit} disabled={busy}>
          {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </div>
    </main>
  );
}
