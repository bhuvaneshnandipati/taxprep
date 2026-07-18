"use client";
import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiJson, token, downloadPackage, uploadDocument } from "@/lib/api";
import Ledger, { CalcResult } from "@/components/Ledger";

type Q = { id: string; section: string; text: string; type: string; options?: string[] };
type W2 = { employer: string; wages: number; fed_withholding: number; state_withholding: number };

const STEPS = ["About you", "Residency", "Interview", "Income", "Results"];

export default function ReturnWizard() {
  const { id } = useParams<{ id: string }>();
  const rid = Number(id);
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  // step 0 — taxpayer
  const [tp, setTp] = useState({ first_name: "", last_name: "", ssn: "", address: "", city_state_zip: "", school: "" });
  // step 1 — residency profile
  const [prof, setProf] = useState({ citizen: false, green_card: false, visa: "F-1", country: "India",
    first_entry_year: 2023, days_current: 365, days_prior1: 0, days_prior2: 0, is_student: true });
  const [citAns, setCitAns] = useState<"" | "yes" | "no">("");
  const [gcAns, setGcAns] = useState<"" | "yes" | "no">("");
  const [residency, setResidency] = useState<any>(null);
  // step 2 — adaptive interview
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [queue, setQueue] = useState<Q[]>([]);
  const [progressPct, setProgressPct] = useState(0);
  // step 3 — income
  const [inc, setInc] = useState({
    filing_status: "single", w2s: [{ employer: "", wages: 0, fed_withholding: 0, state_withholding: 0 }] as W2[],
    interest: 0, dividends: 0, qualified_dividends: 0, capital_gain_lt: 0, capital_gain_st: 0,
    state: "CA", se_income: 0, scholarship_taxable: 0, student_loan_interest: 0, itemized: 0,
    tuition_paid: 0, education_credit_type: "none", qualifying_children: 0, other_dependents: 0,
    estimated_payments: 0, ca_full_year_resident: true, ca_income_ratio: 1, ca_renter: false,
  });
  const [result, setResult] = useState<CalcResult>(null);
  const [ocr, setOcr] = useState<{ busy: boolean; doc: any | null; err: string }>({ busy: false, doc: null, err: "" });

  useEffect(() => { if (!token()) router.push("/"); }, [router]);

  const isNRA = residency?.status === "nonresident";

  /* ---------- actions ---------- */
  const saveTaxpayer = async () => {
    await apiJson(`/returns/${rid}/taxpayer`, { method: "PUT", body: JSON.stringify(tp) });
  };
  const saveProfile = async () => {
    const body = { ...prof, citizen: citAns === "yes", green_card: gcAns === "yes" };
    const out = await apiJson(`/returns/${rid}/profile`, { method: "PUT", body: JSON.stringify(body) });
    setResidency(out.residency);
    return out.residency;
  };
  const syncAnswers = async (a: Record<string, any>) => {
    const out = await apiJson(`/returns/${rid}/answers`, { method: "PUT",
      body: JSON.stringify({ answers: a }) });
    setQueue(out.next_questions);
    setProgressPct(out.progress.pct);
  };
  const answer = async (q: Q, val: any) => {
    const a = { ...answers, [q.id]: val };
    // mirror interview answers into income where they map
    if (q.id === "num_children") setInc((p) => ({ ...p, qualifying_children: Number(val) || 0 }));
    if (q.id === "ca_residency") setInc((p) => ({ ...p, ca_full_year_resident: val === "yes" }));
    if (q.id === "ca_income_pct") setInc((p) => ({ ...p, ca_income_ratio: (Number(val) || 100) / 100 }));
    setAnswers(a);
    await syncAnswers(a);
  };
  const calculate = async () => {
    setBusy(true); setErr("");
    try {
      await apiJson(`/returns/${rid}/income`, { method: "PUT", body: JSON.stringify(inc) });
      const out = await apiJson(`/returns/${rid}/calculate`, { method: "POST" });
      setResult(out);
      setStep(4);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  const next = async () => {
    setErr(""); setBusy(true);
    try {
      if (step === 0) await saveTaxpayer();
      if (step === 1) {
        const res = await saveProfile();
        await syncAnswers({ ...answers, citizen: citAns, green_card: gcAns, _residency: res.status });
        setAnswers((a) => ({ ...a, citizen: citAns, green_card: gcAns, _residency: res.status }));
      }
      if (step === 3) { await calculate(); return; }
      setStep(step + 1);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const handleUpload = async (file: File) => {
    setOcr({ busy: true, doc: null, err: "" });
    try {
      const out = await uploadDocument(rid, file);
      setOcr({ busy: false, doc: out, err: "" });
    } catch (e: any) { setOcr({ busy: false, doc: null, err: e.message }); }
  };
  const applyDoc = async () => {
    const d = ocr.doc;
    const out = await apiJson(`/returns/${rid}/documents/${d.id}/apply`, { method: "POST" });
    const w2s = out.income.w2s || [];
    if (d.doc_type === "W-2" && w2s.length) {
      setInc((p) => ({ ...p, w2s: w2s.map((w: any) => ({
        employer: w.employer || "", wages: w.wages || 0,
        fed_withholding: w.fed_withholding || 0, state_withholding: w.state_withholding || 0 })) }));
    }
    if (d.doc_type === "1099-INT") setInc((p) => ({ ...p, interest: out.income.interest || 0 }));
    if (d.doc_type === "1099-DIV") setInc((p) => ({ ...p, dividends: out.income.dividends || 0 }));
    if (d.doc_type === "1099-NEC") setInc((p) => ({ ...p, se_income: out.income.se_income || 0 }));
    setOcr({ busy: false, doc: null, err: "" });
  };

  const setW2 = (i: number, k: keyof W2, v: any) =>
    setInc((p) => { const w = [...p.w2s]; (w[i] as any)[k] = k === "employer" ? v : Number(v) || 0; return { ...p, w2s: w }; });

  const YesNo = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <div className="flex gap-2">
      {["yes", "no"].map((o) => (
        <button key={o} className={`chip ${value === o ? "chip-on" : "chip-off"}`} onClick={() => onChange(o)}>
          {o === "yes" ? "Yes" : "No"}
        </button>
      ))}
    </div>
  );
  const Num = ({ value, onChange, placeholder }: any) => (
    <input className="inp" inputMode="decimal" value={value || ""} placeholder={placeholder || "0"}
           onChange={(e) => onChange(e.target.value)} />
  );

  /* ---------- step bodies ---------- */
  const body = useMemo(() => {
    if (step === 0) return (
      <>
        <h2 className="text-2xl font-bold mb-5">Let&apos;s start with you</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <div><label className="lbl">First name</label><input className="inp" value={tp.first_name} onChange={(e) => setTp({ ...tp, first_name: e.target.value })} /></div>
          <div><label className="lbl">Last name</label><input className="inp" value={tp.last_name} onChange={(e) => setTp({ ...tp, last_name: e.target.value })} /></div>
          <div><label className="lbl">SSN or ITIN</label><input className="inp" value={tp.ssn} onChange={(e) => setTp({ ...tp, ssn: e.target.value })} placeholder="XXX-XX-XXXX" /></div>
          <div><label className="lbl">Filing status</label>
            <select className="inp" value={inc.filing_status} onChange={(e) => setInc({ ...inc, filing_status: e.target.value })}>
              <option value="single">Single</option><option value="mfj">Married filing jointly</option>
              <option value="mfs">Married filing separately</option><option value="hoh">Head of household</option>
            </select></div>
          <div className="sm:col-span-2"><label className="lbl">Home address</label><input className="inp" value={tp.address} onChange={(e) => setTp({ ...tp, address: e.target.value })} /></div>
          <div className="sm:col-span-2"><label className="lbl">City, state, ZIP</label><input className="inp" value={tp.city_state_zip} onChange={(e) => setTp({ ...tp, city_state_zip: e.target.value })} /></div>
        </div>
      </>
    );
    if (step === 1) return (
      <>
        <h2 className="text-2xl font-bold mb-5">Residency for tax purposes</h2>
        <div className="space-y-5">
          <div><label className="lbl">Are you a U.S. citizen?</label><YesNo value={citAns} onChange={(v) => setCitAns(v as any)} /></div>
          {citAns === "no" && (
            <>
              <div><label className="lbl">Do you have a green card?</label><YesNo value={gcAns} onChange={(v) => setGcAns(v as any)} /></div>
              {gcAns === "no" && (
                <>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div><label className="lbl">Visa / status in 2025</label>
                      <select className="inp" value={prof.visa} onChange={(e) => setProf({ ...prof, visa: e.target.value })}>
                        {["F-1","J-1 Student","J-1 Non-student","M-1","H-1B","H-2A","H-2B","L-1","O-1","TN","E-1","E-2","E-3","OPT","STEM OPT","CPT","B1/B2","K","Asylum","Refugee","Other"].map((v) => <option key={v}>{v}</option>)}
                      </select></div>
                    <div><label className="lbl">Country of citizenship</label>
                      <input className="inp" value={prof.country} onChange={(e) => setProf({ ...prof, country: e.target.value })} /></div>
                    <div><label className="lbl">First entry year (this status)</label>
                      <Num value={prof.first_entry_year} onChange={(v: string) => setProf({ ...prof, first_entry_year: Number(v) || 0 })} /></div>
                    <div><label className="lbl">Enrolled student?</label>
                      <YesNo value={prof.is_student ? "yes" : "no"} onChange={(v) => setProf({ ...prof, is_student: v === "yes" })} /></div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    {(["days_current", "days_prior1", "days_prior2"] as const).map((k, i) => (
                      <div key={k}><label className="lbl">Days in U.S. {2025 - i}</label>
                        <Num value={(prof as any)[k]} onChange={(v: string) => setProf({ ...prof, [k]: Number(v) || 0 })} /></div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
          {residency && (
            <div className="card border-l-4 border-l-formblue">
              <div className="font-mono text-[11px] tracking-wider text-gray-500 mb-1">DETERMINATION · TY 2025</div>
              <div className="text-xl font-bold">{residency.label}</div>
              <div className="text-formblue font-semibold text-sm mb-2">
                Form {residency.form}{residency.form_8843_required ? " + Form 8843" : ""}
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">{residency.explanation}</p>
            </div>
          )}
        </div>
      </>
    );
    if (step === 2) return (
      <>
        <div className="flex items-baseline justify-between mb-5">
          <h2 className="text-2xl font-bold">A few questions</h2>
          <span className="font-mono text-[12px] text-gray-500">{progressPct}% COMPLETE</span>
        </div>
        {queue.length === 0 ? (
          <div className="card text-center py-10">
            <p className="font-semibold">Interview complete</p>
            <p className="text-sm text-gray-500">Continue to enter your income documents.</p>
          </div>
        ) : (
          <div className="space-y-5">
            {queue.map((q) => (
              <div key={q.id} className="card">
                <div className="font-mono text-[10px] tracking-wider text-gray-400 uppercase mb-1">{q.section}</div>
                <p className="font-semibold mb-3">{q.text}</p>
                {q.type === "yesno" && <YesNo value={answers[q.id] || ""} onChange={(v) => answer(q, v)} />}
                {q.type === "number" && (
                  <input className="inp max-w-[200px]" inputMode="numeric" defaultValue={answers[q.id] || ""}
                         onBlur={(e) => e.target.value !== "" && answer(q, e.target.value)}
                         onKeyDown={(e: any) => e.key === "Enter" && e.target.value !== "" && answer(q, e.target.value)} />
                )}
                {(q.type === "select") && (
                  <select className="inp max-w-[280px]" value={answers[q.id] || ""} onChange={(e) => answer(q, e.target.value)}>
                    <option value="" disabled>Choose…</option>
                    {q.options?.map((o) => <option key={o}>{o}</option>)}
                  </select>
                )}
                {q.type === "text" && (
                  <input className="inp max-w-[280px]" defaultValue={answers[q.id] || ""}
                         onBlur={(e) => e.target.value !== "" && answer(q, e.target.value)} />
                )}
              </div>
            ))}
          </div>
        )}
      </>
    );
    if (step === 3) return (
      <>
        <h2 className="text-2xl font-bold mb-5">Income &amp; deductions</h2>
        <div className="mb-5 max-w-[320px]"><label className="lbl">State (2025)</label>
          <select className="inp" value={inc.state} onChange={(e) => setInc({ ...inc, state: e.target.value })}>
            <option value="CA">California</option>
            <option value="NY">New York</option>
            <optgroup label="No state income tax">
              {["AK","FL","NV","NH","SD","TN","TX","WA","WY"].map((s) => <option key={s} value={s}>{s}</option>)}
            </optgroup>
          </select></div>
        <div className="card mb-5 border-dashed">
          <div className="font-mono text-[11px] text-formblue mb-2 tracking-wider">UPLOAD A DOCUMENT — W-2, 1099-INT, 1099-DIV, 1099-NEC</div>
          <p className="text-sm text-gray-500 mb-3">PDF, JPG, or PNG. We read the boxes automatically; you review before anything is added.</p>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png,.heic" className="text-sm"
                 onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])} />
          {ocr.busy && <p className="text-sm text-formblue mt-2">Reading document…</p>}
          {ocr.err && <p className="text-sm text-owe mt-2">{ocr.err}</p>}
          {ocr.doc && (
            <div className="mt-4 border-t border-rule pt-3">
              <div className="font-semibold text-sm mb-2">
                Detected: {ocr.doc.doc_type}
                {ocr.doc.extracted.needs_review && <span className="ml-2 text-xs font-mono text-owe">REVIEW LOW-CONFIDENCE FIELDS</span>}
              </div>
              <div className="grid sm:grid-cols-2 gap-2 mb-3">
                {Object.entries(ocr.doc.extracted.fields as Record<string, any>).map(([k, f]) => (
                  <div key={k} className="text-sm flex justify-between gap-2 border-b border-dotted border-rule py-1">
                    <span className="text-gray-500">{k.replace(/_/g, " ")}</span>
                    <span className={`font-mono ${f.confidence < 0.8 ? "text-owe" : ""}`}>
                      {typeof f.value === "number" ? f.value.toLocaleString() : f.value}
                    </span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <button className="btn" onClick={applyDoc}>Looks right — add to my return</button>
                <button className="btn-ghost" onClick={() => setOcr({ busy: false, doc: null, err: "" })}>Discard — I&apos;ll type it</button>
              </div>
            </div>
          )}
        </div>
        {inc.w2s.map((w, i) => (
          <div key={i} className="card mb-4">
            <div className="font-mono text-[11px] text-formblue mb-3">W-2 #{i + 1}</div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2"><label className="lbl">Employer</label>
                <input className="inp" value={w.employer} onChange={(e) => setW2(i, "employer", e.target.value)} /></div>
              <div><label className="lbl">Box 1 — wages</label><Num value={w.wages} onChange={(v: string) => setW2(i, "wages", v)} /></div>
              <div><label className="lbl">Box 2 — federal withheld</label><Num value={w.fed_withholding} onChange={(v: string) => setW2(i, "fed_withholding", v)} /></div>
              <div><label className="lbl">Box 17 — CA withheld</label><Num value={w.state_withholding} onChange={(v: string) => setW2(i, "state_withholding", v)} /></div>
            </div>
          </div>
        ))}
        <button className="btn-ghost mb-6" onClick={() => setInc((p) => ({ ...p, w2s: [...p.w2s, { employer: "", wages: 0, fed_withholding: 0, state_withholding: 0 }] }))}>
          + Add another W-2
        </button>
        <div className="grid sm:grid-cols-2 gap-4">
          {answers.has_interest === "yes" && (
            <div><label className="lbl">Interest income (1099-INT)</label>
              <Num value={inc.interest} onChange={(v: string) => setInc({ ...inc, interest: Number(v) || 0 })} /></div>)}
          {answers.has_dividends === "yes" && !isNRA && (
            <div><label className="lbl">Ordinary dividends (1099-DIV)</label>
              <Num value={inc.dividends} onChange={(v: string) => setInc({ ...inc, dividends: Number(v) || 0 })} /></div>)}
          {answers.has_capital_gains === "yes" && (
            <>
              <div><label className="lbl">Long-term gains</label>
                <Num value={inc.capital_gain_lt} onChange={(v: string) => setInc({ ...inc, capital_gain_lt: Number(v) || 0 })} /></div>
              <div><label className="lbl">Short-term gains</label>
                <Num value={inc.capital_gain_st} onChange={(v: string) => setInc({ ...inc, capital_gain_st: Number(v) || 0 })} /></div>
            </>)}
          {answers.has_self_employment === "yes" && !isNRA && (
            <div><label className="lbl">Self-employment income (1099-NEC)</label>
              <Num value={inc.se_income} onChange={(v: string) => setInc({ ...inc, se_income: Number(v) || 0 })} /></div>)}
          {answers.student_loan === "yes" && (
            <div><label className="lbl">Student loan interest (1098-E)</label>
              <Num value={inc.student_loan_interest} onChange={(v: string) => setInc({ ...inc, student_loan_interest: Number(v) || 0 })} /></div>)}
          {answers.tuition_paid === "yes" && !isNRA && (
            <>
              <div><label className="lbl">Tuition paid (1098-T)</label>
                <Num value={inc.tuition_paid} onChange={(v: string) => setInc({ ...inc, tuition_paid: Number(v) || 0 })} /></div>
              <div><label className="lbl">Education credit</label>
                <select className="inp" value={inc.education_credit_type} onChange={(e) => setInc({ ...inc, education_credit_type: e.target.value })}>
                  <option value="none">None</option><option value="aotc">American Opportunity</option><option value="llc">Lifetime Learning</option>
                </select></div>
            </>)}
          {isNRA && prof.country.trim().toLowerCase() !== "india" && (
            <div><label className="lbl">State tax withheld (itemized deduction)</label>
              <Num value={inc.itemized} onChange={(v: string) => setInc({ ...inc, itemized: Number(v) || 0 })} /></div>)}
        </div>
      </>
    );
    /* results */
    if (!result) return <p className="text-gray-500">Calculating…</p>;
    const F = result.federal, C = result.state;
    return (
      <>
        <h2 className="text-2xl font-bold mb-5">Your 2025 results</h2>
        <div className="grid sm:grid-cols-2 gap-4 mb-6">
          {[{ t: "Federal", f: F.form, r: F.lines.refund },
            ...(C.form === "none" ? [] : [{ t: (C as any).state === "NY" ? "New York" : "California", f: C.form, r: C.lines.refund }])].map((x) => (
            <div key={x.t} className="card border-t-4" style={{ borderTopColor: x.r >= 0 ? "#1E7A4D" : "#B3382C" }}>
              <div className="lbl mb-0">{x.t} · Form {x.f}</div>
              <div className="font-mono text-3xl font-bold my-1" style={{ color: x.r >= 0 ? "#1E7A4D" : "#B3382C" }}>
                ${Math.abs(x.r).toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">{x.r >= 0 ? "Refund" : "Amount you owe"}</div>
            </div>
          ))}
        </div>
        <button className="btn w-full sm:w-auto mb-8" onClick={() => downloadPackage(rid, 2025)}>
          Download filing package (PDF)
        </button>
        <h3 className="font-bold mb-2">How your tax was calculated</h3>
        <div className="card mb-6 space-y-2">
          {[...F.explanations, ...C.explanations].map((e, i) => (
            <p key={i} className="text-sm text-gray-600">• {e}</p>
          ))}
        </div>
        <h3 className="font-bold mb-2">Filing checklist</h3>
        <div className="card">
          {result.checklist.map((c, i) => (
            <div key={i} className="flex gap-2.5 py-2 border-b border-dotted border-rule last:border-0 text-sm">
              <span className="font-mono text-formblue">☐</span>{c}
            </div>
          ))}
        </div>
      </>
    );
  }, [step, tp, citAns, gcAns, prof, residency, queue, answers, progressPct, inc, result, isNRA, rid]);

  return (
    <div className="max-w-[1060px] mx-auto px-5 pb-24 lg:pb-14">
      <div className="flex gap-1 flex-wrap pt-4">
        {STEPS.map((s, i) => (
          <button key={s} onClick={() => i < step && setStep(i)}
            className={`px-3 py-1.5 text-xs font-mono rounded ${i === step ? "bg-formblue text-white font-bold" : i < step ? "text-formblue" : "text-gray-400"}`}>
            {i + 1} {s}
          </button>
        ))}
      </div>
      <div className="flex gap-6 items-start pt-5">
        <main className="flex-1 min-w-0">
          {body}
          {err && <p className="text-sm text-owe mt-4">{err}</p>}
          {step < 4 && (
            <div className="flex gap-3 mt-8">
              {step > 0 && <button className="btn-ghost" onClick={() => setStep(step - 1)}>Back</button>}
              <button className="btn" onClick={next} disabled={busy || (step === 1 && !citAns)}>
                {busy ? "Working…" : step === 3 ? "Calculate my return" : "Continue"}
              </button>
            </div>
          )}
        </main>
        <Ledger result={result} />
      </div>
    </div>
  );
}
