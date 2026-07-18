"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson, token, clearToken } from "@/lib/api";

type Ret = { id: number; tax_year: number; status: string; updated_at: string };

export default function Dashboard() {
  const r = useRouter();
  const [returns, setReturns] = useState<Ret[] | null>(null);

  useEffect(() => {
    if (!token()) { r.push("/"); return; }
    apiJson("/returns").then(setReturns).catch(() => r.push("/"));
  }, [r]);

  const create = async () => {
    const nr = await apiJson("/returns", { method: "POST" });
    r.push(`/return/${nr.id}`);
  };

  return (
    <main className="max-w-3xl mx-auto px-5 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Your returns</h1>
        <div className="flex gap-3">
          <button className="btn" onClick={create}>Start 2025 return</button>
          <button className="btn-ghost" onClick={() => { clearToken(); r.push("/"); }}>Sign out</button>
        </div>
      </div>
      {returns === null ? <p className="text-gray-500">Loading…</p> :
       returns.length === 0 ? (
        <div className="card text-center py-12">
          <p className="font-semibold mb-1">No returns yet</p>
          <p className="text-sm text-gray-500">Start your 2025 federal + California return — it takes about 15 minutes.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {returns.map((x) => (
            <a key={x.id} href={`/return/${x.id}`} className="card flex items-center justify-between hover:border-formblue">
              <div>
                <div className="font-semibold">Tax year {x.tax_year}</div>
                <div className="text-xs text-gray-500 font-mono">Updated {x.updated_at?.slice(0, 16)}</div>
              </div>
              <span className={`text-xs font-mono px-2 py-1 rounded ${x.status === "complete" ? "bg-refund/10 text-refund" : "bg-bluesoft text-formblue"}`}>
                {x.status === "complete" ? "COMPLETE" : "IN PROGRESS"}
              </span>
            </a>
          ))}
        </div>
      )}
    </main>
  );
}
