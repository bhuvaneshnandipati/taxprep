"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson, token } from "@/lib/api";

type Tab = "users" | "audit" | "review" | "rules";

export default function AdminPage() {
  const r = useRouter();
  const [tab, setTab] = useState<Tab>("users");
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState("");
  const [packSel, setPackSel] = useState<{ year: string; pack: string } | null>(null);
  const [packBody, setPackBody] = useState("");

  const load = async (t: Tab) => {
    setErr(""); setData(null); setPackSel(null);
    try {
      if (t === "users") setData(await apiJson("/admin/users"));
      if (t === "audit") setData(await apiJson("/admin/audit"));
      // NOTE: /admin/audit now returns { retention_months, entries }
      if (t === "review") setData(await apiJson("/admin/documents/review-queue"));
      if (t === "rules") setData(await apiJson("/admin/rules"));
    } catch (e: any) { setErr(e.message); }
  };
  useEffect(() => { if (!token()) { r.push("/"); return; } load(tab); /* eslint-disable-next-line */ }, [tab]);

  const openPack = async (year: string, pack: string) => {
    setPackSel({ year, pack });
    setPackBody(JSON.stringify(await apiJson(`/admin/rules/${year}/${pack}`), null, 2));
  };
  const savePack = async () => {
    try {
      await apiJson(`/admin/rules/${packSel!.year}/${packSel!.pack}`,
        { method: "PUT", body: packBody });
      setErr(""); alert("Rule pack saved. Previous version backed up as .bak.");
    } catch (e: any) { setErr(e.message); }
  };
  const purgeAudit = async () => {
    const out = await apiJson("/admin/audit/purge", { method: "POST" });
    alert(`Removed ${out.deleted} entries older than 5 months.`);
    load("audit");
  };
  const setRole = async (uid: number, role: string) => {
    await apiJson(`/admin/users/${uid}/role`, { method: "PUT", body: JSON.stringify({ role }) });
    load("users");
  };

  return (
    <main className="max-w-5xl mx-auto px-5 py-8">
      <h1 className="text-2xl font-bold mb-4">Admin</h1>
      <div className="flex gap-2 mb-5">
        {(["users", "audit", "review", "rules"] as Tab[]).map((t) => (
          <button key={t} className={`chip ${tab === t ? "chip-on" : "chip-off"}`} onClick={() => setTab(t)}>
            {{ users: "Users", audit: "Audit log", review: "OCR review queue", rules: "Tax rules" }[t]}
          </button>
        ))}
      </div>
      {err && <p className="text-sm text-owe mb-4">{err}</p>}
      {!data && !err && <p className="text-gray-500 text-sm">Loading…</p>}

      {tab === "users" && data && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left font-mono text-[11px] text-gray-500 uppercase">
              <th className="py-2">Email</th><th>Name</th><th>Role</th><th>Returns</th><th>Joined</th><th></th></tr></thead>
            <tbody>{data.map((u: any) => (
              <tr key={u.id} className="border-t border-rule">
                <td className="py-2">{u.email}</td><td>{u.full_name}</td>
                <td className="font-mono text-xs">{u.role}</td><td>{u.returns}</td>
                <td className="text-xs text-gray-500">{u.created_at?.slice(0, 10)}</td>
                <td><button className="text-formblue text-xs underline"
                     onClick={() => setRole(u.id, u.role === "admin" ? "user" : "admin")}>
                     {u.role === "admin" ? "demote" : "make admin"}</button></td>
              </tr>))}</tbody>
          </table>
        </div>
      )}

      {tab === "audit" && data && (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-gray-500">
              Entries older than {data.retention_months} months are purged automatically each time this log is viewed.
            </p>
            <button className="btn-ghost !py-1.5 !px-3 text-sm" onClick={purgeAudit}>Purge now</button>
          </div>
          <div className="card font-mono text-xs space-y-1 max-h-[60vh] overflow-y-auto">
            {data.entries.map((a: any, i: number) => (
              <div key={i} className="border-b border-dotted border-rule py-1">
                {a.at?.slice(0, 19)} · {a.user} · <b>{a.action}</b> {a.detail && `· ${a.detail}`}
              </div>))}
          </div>
        </>
      )}

      {tab === "review" && data && (
        data.length === 0 ? <div className="card text-sm text-gray-500">No documents awaiting review.</div> :
        <div className="space-y-2">{data.map((d: any) => (
          <div key={d.id} className="card text-sm flex justify-between">
            <span>#{d.id} · return {d.return_id} · {d.filename} · <b>{d.doc_type}</b></span>
            <span className="font-mono text-xs text-owe">{d.low_confidence_fields.join(", ")}</span>
          </div>))}</div>
      )}

      {tab === "rules" && data && !packSel && (
        <div className="card text-sm">
          {Object.entries(data as Record<string, string[]>).map(([year, packs]) => (
            <div key={year} className="mb-3">
              <div className="font-mono text-[11px] text-gray-500 mb-1">TAX YEAR {year}</div>
              <div className="flex gap-2 flex-wrap">
                {packs.map((p) => (
                  <button key={p} className="chip chip-off" onClick={() => openPack(year, p)}>{p}</button>))}
              </div>
            </div>))}
        </div>
      )}
      {tab === "rules" && packSel && (
        <div className="card">
          <div className="flex justify-between items-center mb-2">
            <span className="font-mono text-sm">{packSel.year}/{packSel.pack}.yaml</span>
            <div className="flex gap-2">
              <button className="btn-ghost !py-1.5 !px-3 text-sm" onClick={() => setPackSel(null)}>Back</button>
              <button className="btn !py-1.5 !px-3 text-sm" onClick={savePack}>Save (with backup)</button>
            </div>
          </div>
          <textarea className="w-full h-[55vh] font-mono text-xs border-[1.5px] border-rule rounded-md p-3"
                    value={packBody} onChange={(e) => setPackBody(e.target.value)} />
        </div>
      )}
    </main>
  );
}
