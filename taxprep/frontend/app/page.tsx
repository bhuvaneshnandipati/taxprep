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
    <main className="max-w-6xl mx-auto px-5 py-10 sm:py-16 grid gap-12 lg:grid-cols-[1.15fr_1fr] lg:gap-16 items-center">
      <section>
        <p className="kicker mb-4 flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-refund" />Built for F-1, J-1 &amp; H-1B filers</p>
        <h1 className="text-[2.6rem] sm:text-6xl font-extrabold leading-[1.02] mb-5">Your 2025 return,<br /><span className="mark">line by line.</span></h1>
        <p className="text-lg text-gray-600 max-w-[50ch] mb-8">Residency test, Form 8843, 1040-NR with tax treaties, dual-status, plus California and New York, with every number posted to the real form line as you go.</p>
        <div aria-hidden="true" className="relative max-w-md">
          <div className="absolute inset-0 translate-x-3 translate-y-3 rounded-2xl bg-ink/90" />
          <div className="relative card p-0 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-hair bg-paper/60">
              <span className="font-mono text-[11px] tracking-[0.1em] text-mute">FORM 1040 · EXAMPLE</span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-refund/10 text-refund">CALCULATED</span>
            </div>
            <div className="px-5 py-3 font-mono text-[13px]">
              {[["1a", "Wages", "$45,000"], ["11", "Adjusted gross income", "$45,000"], ["12", "Standard deduction", "−$15,750"], ["16", "Tax", "$3,275"], ["25", "Federal tax withheld", "$4,200"]].map(([l, d, v], i) => (
                <div key={l} className="flex gap-3 py-1.5 border-b border-dashed border-hair animate-post" style={{ animationDelay: `${150 + i * 120}ms` }}>
                  <span className="w-7 text-formblue">{l}</span><span className="flex-1 font-sans text-gray-600">{d}</span><span>{v}</span>
                </div>))}
              <div className="flex gap-3 pt-3 pb-1 items-baseline animate-post" style={{ animationDelay: "800ms" }}>
                <span className="w-7 text-formblue">34</span><span className="flex-1 font-sans font-semibold">Refund</span>
                <span className="text-2xl font-bold text-refund">$925</span>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section aria-label="Account">
      {!available && <p className="text-sm mb-4">Hosted backend unavailable: account creation and sign-in are disabled until the replacement API is verified.</p>}
      <div className="card p-6 sm:p-8 shadow-lift"><h2 className="text-2xl mb-1">{mode === "login" ? "Welcome back" : "Create your account"}</h2><p className="text-sm text-mute mb-6">{mode === "login" ? "Sign in to resume a saved return." : "Takes about 15 minutes to finish a return."}</p>
      <form onSubmit={(e) => { e.preventDefault(); if (!busy) submit(); }}>
        <div className="flex gap-1 mb-6 p-1 rounded-full bg-paper border border-hair w-fit">
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
      </form></div>
      </section>
    </main>
  );
}
