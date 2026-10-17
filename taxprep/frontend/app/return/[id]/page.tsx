"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiJson, token, downloadPackage, uploadDocument } from "@/lib/api";
import Ledger, { CalcResult, Residency, GREEN, RED } from "@/components/Ledger";
import { MoneyInput, YesNo, Field, TextInput } from "@/components/Fields";

type Q = { id: string; section: string; text: string; type: string; options?: string[]; help?: string };
type W2 = { employer: string; ein: string; wages: number; fed_withholding: number; ss_wages: number; ss_tax: number;
  medicare_wages: number | null; medicare_tax: number; state: string; state_wages: number; state_withholding: number };

const STEPS = ["About you", "Residency", "Interview", "Income", "Results"];
const TAX_YEAR = 2025;
const VISAS = ["F-1", "OPT", "STEM OPT", "CPT", "J-1 Student", "J-1 Non-student", "M-1", "Q-1", "H-1B", "H-4",
  "L-1", "O-1", "TN", "E-2", "E-3", "B1/B2", "Other"];
const EXEMPT = new Set(["F-1", "OPT", "STEM OPT", "CPT", "J-1 Student", "J-1 Non-student", "M-1", "Q-1"]);
const STATES: [string, string][] = [["CA", "California"], ["NY", "New York"]];
const NO_TAX = ["AK", "FL", "NV", "NH", "SD", "TN", "TX", "WA", "WY"];

const emptyW2 = (state = "CA"): W2 => ({ employer: "", ein: "", wages: 0, fed_withholding: 0, ss_wages: 0, ss_tax: 0,
  medicare_wages: null, medicare_tax: 0, state, state_wages: 0, state_withholding: 0 });

const blankTaxpayer = { first_name: "", middle_initial: "", last_name: "", ssn: "", date_of_birth: "", occupation: "",
  phone: "", email: "", address: "", apt: "", city: "", state: "", zip: "", city_state_zip: "",
  foreign_country: "", foreign_province: "", foreign_postal: "", school: "", school_address: "" };

const blankProfile = { citizen: false, green_card: false, visa: "F-1", country: "", first_entry_year: 0,
  days_current: 0, days_prior1: 0, days_prior2: 0, exempt_days_current: null as number | null,
  exempt_days_prior1: null as number | null, exempt_days_prior2: null as number | null,
  first_nonexempt_day: "", is_student: true, visa_entry_date: "", visa_history: "", school_phone: "",
  program_director: "", previous_visa: "", visa_by_year: {} as Record<string, string>, passport_country: "",
  passport_number: "", tax_residence_country: "", applied_green_card: false, filed_prior_return: false,
  prior_return_info: "", treaty_prior_months: 0, trips: [] as { entered: string; departed: string }[],
  health_coverage: true };

const blankIncome = {
  filing_status: "single", w2s: [emptyW2()] as W2[], wages_nr_period: 0,
  comp_1042s: 0, scholarship_1042s: 0, withholding_1042s: 0,
  interest: 0, dividends: 0, qualified_dividends: 0, capital_gain_lt: 0, capital_gain_st: 0, se_income: 0,
  scholarship_taxable: 0, withholding_1099: 0, student_loan_interest: 0, itemized: 0, state_tax_other: 0,
  charitable: 0, other_itemized: 0, qualified_tips: 0, qualified_overtime: 0, has_ssn: true, age: 0,
  tuition_paid: 0, education_credit_type: "none", qualifying_children: 0, other_dependents: 0,
  estimated_payments: 0, state: "CA", ca_full_year_resident: true, ca_income_ratio: 1,
  state_source_income: null as number | null, state_itemized: 0, ca_renter: false,
};

export default function ReturnWizard() {
  const { id } = useParams<{ id: string }>();
  const rid = Number(id);
  const router = useRouter();
  const [loaded, setLoaded] = useState(false);
  const [step, setStep] = useState(0);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const [tp, setTp] = useState(blankTaxpayer);
  const [prof, setProf] = useState(blankProfile);
  const [citAns, setCitAns] = useState<"" | "yes" | "no">("");
  const [gcAns, setGcAns] = useState<"" | "yes" | "no">("");
  const [statusChanged, setStatusChanged] = useState(false);
  const [tripsText, setTripsText] = useState("");
  const [residency, setResidency] = useState<Residency | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [queue, setQueue] = useState<Q[]>([]);
  const [progressPct, setProgressPct] = useState(0);
  const [inc, setInc] = useState(blankIncome);
  const [result, setResult] = useState<CalcResult>(null);
  const [ocr, setOcr] = useState<{ busy: boolean; doc: any | null; err: string }>({ busy: false, doc: null, err: "" });

  /* ---------- load / resume ---------- */
  useEffect(() => {
    if (!token()) { router.push("/"); return; }
    apiJson(`/returns/${rid}`).then((d) => {
      if (d.taxpayer) setTp({ ...blankTaxpayer, ...d.taxpayer });
      if (d.profile) {
        const p = { ...blankProfile, ...d.profile };
        setProf(p);
        setCitAns(p.citizen ? "yes" : "no");
        setGcAns(p.citizen ? "" : p.green_card ? "yes" : "no");
        setStatusChanged(p.exempt_days_current !== null || p.exempt_days_prior1 !== null || !!p.first_nonexempt_day);
        setTripsText((p.trips || []).map((t: any) => `${t.entered || ""} ${t.departed || ""}`.trim()).join("\n"));
      }
      if (d.income) setInc({ ...blankIncome, ...d.income, w2s: d.income.w2s?.length ? d.income.w2s.map((w: any) => ({ ...emptyW2(), ...w })) : [emptyW2()] });
      setResidency(d.residency);
      setAnswers(d.answers || {});
      setQueue(d.next_questions || []);
      setProgressPct(d.progress?.pct || 0);
      setResult(d.result);
      setStep(d.result ? 4 : d.income ? 3 : d.profile ? 2 : d.taxpayer?.first_name ? 1 : 0);
      setLoaded(true);
    }).catch((e) => { setErr(e.message); setLoaded(true); });
  }, [rid, router]);

  const isNRA = residency?.status === "nonresident";
  const isDual = residency?.status === "dual_status";
  const isResident = !!residency && !isNRA && !isDual;
  const yes = (k: string) => answers[k] === "yes";
  const setI = (patch: Partial<typeof blankIncome>) => setInc((p) => ({ ...p, ...patch }));
  const setP = (patch: Partial<typeof blankProfile>) => setProf((p) => ({ ...p, ...patch }));
  const setT = (patch: Partial<typeof blankTaxpayer>) => setTp((p) => ({ ...p, ...patch }));

  /* ---------- actions ---------- */
  const saveProfile = async () => {
    const trips = tripsText.split("\n").map((l) => l.trim().split(/[\s,]+/)).filter((x) => x[0])
      .slice(0, 8).map(([a, b]) => ({ entered: a || "", departed: b || "" }));
    const body: any = { ...prof, trips, citizen: citAns === "yes", green_card: citAns === "no" && gcAns === "yes" };
    if (!statusChanged) {
      body.exempt_days_current = null; body.exempt_days_prior1 = null; body.exempt_days_prior2 = null;
    }
    const out = await apiJson(`/returns/${rid}/profile`, { method: "PUT", body: JSON.stringify(body) });
    setResidency(out.residency);
    setQueue(out.next_questions); setProgressPct(out.progress.pct);
    setAnswers((a) => ({ ...a, _residency: out.residency.status }));
    return out.residency as Residency;
  };
  const answer = async (q: Q, val: any) => {
    const a = { ...answers, [q.id]: val };
    if (q.id === "num_children") setI({ qualifying_children: Number(val) || 0 });
    if (q.id === "num_other_dependents") setI({ other_dependents: Number(val) || 0 });
    if (q.id === "state_residency") setI({ ca_full_year_resident: val === "yes" });
    if (q.id === "state_renter") setI({ ca_renter: val === "yes" });
    setAnswers(a);
    const out = await apiJson(`/returns/${rid}/answers`, { method: "PUT", body: JSON.stringify({ answers: { [q.id]: val } }) });
    setQueue(out.next_questions); setProgressPct(out.progress.pct);
  };
  const saveIncome = () => apiJson(`/returns/${rid}/income`, { method: "PUT", body: JSON.stringify(inc) });
  const calculate = async () => {
    await saveIncome();
    const out = await apiJson(`/returns/${rid}/calculate`, { method: "POST" });
    setResult(out); setResidency(out.residency);
    setStep(4); window.scrollTo(0, 0);
  };
  const validate = (): string => {
    if (step === 0) {
      if (!tp.first_name.trim() || !tp.last_name.trim()) return "Enter your first and last name.";
      if (tp.ssn && !/^\d{3}-?\d{2}-?\d{4}$/.test(tp.ssn)) return "SSN/ITIN must be 9 digits (XXX-XX-XXXX).";
    }
    if (step === 1) {
      if (!citAns) return "Answer the citizenship question.";
      if (citAns === "no" && !gcAns) return "Answer the green card question.";
      if (citAns === "no" && gcAns === "no") {
        if (!prof.country.trim()) return "Enter your country of citizenship.";
        if (!prof.first_entry_year || prof.first_entry_year < 1950 || prof.first_entry_year > TAX_YEAR)
          return "Enter the year you first came to the U.S. (e.g. 2022).";
        if (prof.days_current < 1) return `Enter the number of days you were in the U.S. in ${TAX_YEAR}.`;
      }
    }
    return "";
  };
  const next = async () => {
    const v = validate();
    if (v) { setErr(v); return; }
    setErr(""); setBusy(true);
    try {
      if (step === 0) await apiJson(`/returns/${rid}/taxpayer`, { method: "PUT", body: JSON.stringify(tp) });
      if (step === 1) {
        const res = await saveProfile();
        if (res.status === "dual_status" && !prof.first_nonexempt_day) setStatusChanged(true);
      }
      if (step === 2) await saveIncome();
      if (step === 3) { await calculate(); return; }
      setStep(step + 1); window.scrollTo(0, 0);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  const handleUpload = async (file: File) => {
    setOcr({ busy: true, doc: null, err: "" });
    try {
      await saveIncome();           // so the server-side merge starts from what is on screen
      setOcr({ busy: false, doc: await uploadDocument(rid, file), err: "" });
    } catch (e: any) { setOcr({ busy: false, doc: null, err: e.message }); }
  };
  const applyDoc = async () => {
    try {
      const out = await apiJson(`/returns/${rid}/documents/${ocr.doc.id}/apply`, { method: "POST" });
      const i = out.income;
      setInc((p) => ({ ...p, ...i, w2s: (i.w2s || []).length ? i.w2s.map((w: any) => ({ ...emptyW2(p.state), ...w })) : p.w2s }));
      setOcr({ busy: false, doc: null, err: "" });
    } catch (e: any) { setOcr((o) => ({ ...o, err: e.message })); }
  };
  const setW2 = (i: number, patch: Partial<W2>) =>
    setInc((p) => ({ ...p, w2s: p.w2s.map((w, j) => (j === i ? { ...w, ...patch } : w)) }));

  if (!loaded) return <p className="max-w-[1060px] mx-auto px-5 py-10 text-gray-500">Loading your return…</p>;

  /* ---------- step bodies ---------- */
  const stepAbout = (
    <>
      <h2 className="text-2xl font-bold mb-5">Let&apos;s start with you</h2>
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="First name"><TextInput value={tp.first_name} onChange={(v) => setT({ first_name: v })} /></Field>
        <Field label="Last name"><TextInput value={tp.last_name} onChange={(v) => setT({ last_name: v })} /></Field>
        <Field label="SSN or ITIN" hint="Leave blank if you have neither — you will need to apply for an ITIN (Form W-7) to file a return with income.">
          <TextInput value={tp.ssn} onChange={(v) => setT({ ssn: v })} placeholder="XXX-XX-XXXX" maxLength={11} /></Field>
        <Field label="Filing status" hint="Nonresident aliens are limited to single / married filing separately.">
          <select className="inp" value={inc.filing_status} onChange={(e) => setI({ filing_status: e.target.value })}>
            <option value="single">Single</option><option value="mfj">Married filing jointly</option>
            <option value="mfs">Married filing separately</option><option value="hoh">Head of household</option>
            <option value="qss">Qualifying surviving spouse</option>
          </select></Field>
        <Field label="Date of birth"><TextInput type="date" value={tp.date_of_birth} onChange={(v) => setT({ date_of_birth: v })} /></Field>
        <Field label="Occupation in the U.S."><TextInput value={tp.occupation} onChange={(v) => setT({ occupation: v })} placeholder="Student" /></Field>
        <Field label="U.S. street address" wide><TextInput value={tp.address} onChange={(v) => setT({ address: v })} /></Field>
        <Field label="Apt."><TextInput value={tp.apt} onChange={(v) => setT({ apt: v })} /></Field>
        <Field label="City"><TextInput value={tp.city} onChange={(v) => setT({ city: v })} /></Field>
        <Field label="State"><TextInput value={tp.state} onChange={(v) => setT({ state: v.toUpperCase().slice(0, 2) })} placeholder="CA" /></Field>
        <Field label="ZIP"><TextInput value={tp.zip} onChange={(v) => setT({ zip: v })} /></Field>
        <Field label="Foreign country (home address abroad, optional)"><TextInput value={tp.foreign_country} onChange={(v) => setT({ foreign_country: v })} /></Field>
        <Field label="Phone"><TextInput value={tp.phone} onChange={(v) => setT({ phone: v })} /></Field>
        <Field label="Email"><TextInput value={tp.email} onChange={(v) => setT({ email: v })} /></Field>
      </div>
    </>
  );

  const stepResidency = (
    <>
      <h2 className="text-2xl font-bold mb-5">Residency for tax purposes</h2>
      <div className="space-y-5">
        <Field label="Are you a U.S. citizen?"><YesNo value={citAns} onChange={(v) => setCitAns(v)} /></Field>
        {citAns === "no" && <Field label="Did you have a green card at any time in 2025?"><YesNo value={gcAns} onChange={(v) => setGcAns(v)} /></Field>}
        {citAns === "no" && gcAns === "no" && (
          <>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label={`Visa / status at the end of ${TAX_YEAR}`}>
                <select className="inp" value={prof.visa} onChange={(e) => {
                  const v = e.target.value;
                  setP({ visa: v, is_student: ["F-1", "OPT", "STEM OPT", "CPT", "J-1 Student", "M-1"].includes(v) ? prof.is_student : false });
                  if (!EXEMPT.has(v)) setStatusChanged(true);
                }}>
                  {VISAS.map((v) => <option key={v}>{v}</option>)}
                </select></Field>
              <Field label="Country of citizenship / tax residence"><TextInput value={prof.country} onChange={(v) => setP({ country: v })} placeholder="India" /></Field>
              <Field label="First year in the U.S." hint="If you were ever on F, J, M or Q status, the first calendar year you were in the U.S. on that status.">
                <MoneyInput integer value={prof.first_entry_year} onChange={(v) => setP({ first_entry_year: v })} placeholder="2022" /></Field>
              <Field label="Student (or on OPT) in 2025?" hint="Used for treaty student articles.">
                <YesNo value={prof.is_student ? "yes" : "no"} onChange={(v) => setP({ is_student: v === "yes" })} /></Field>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {(["days_current", "days_prior1", "days_prior2"] as const).map((k, i) => (
                <Field key={k} label={`Days in U.S. ${TAX_YEAR - i}`}>
                  <MoneyInput integer value={prof[k]} onChange={(v) => setP({ [k]: Math.min(366, v) } as any)} /></Field>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={statusChanged} onChange={(e) => setStatusChanged(e.target.checked)} />
              I was on a different visa in some of these years (e.g. F-1 → H-1B), or I arrived in {TAX_YEAR}
            </label>
            {statusChanged && (
              <div className="card bg-bluesoft/40 space-y-4">
                <p className="text-sm text-gray-600">Of the days above, how many were you on an F, J, M or Q visa (including OPT)?
                  Those days don&apos;t count toward the Substantial Presence Test during your exempt years.</p>
                <div className="grid grid-cols-3 gap-3">
                  {(["exempt_days_current", "exempt_days_prior1", "exempt_days_prior2"] as const).map((k, i) => (
                    <Field key={k} label={`F/J/M/Q days ${TAX_YEAR - i}`}>
                      <MoneyInput integer value={prof[k] ?? 0} onChange={(v) => setP({ [k]: Math.min(366, v) } as any)} /></Field>
                  ))}
                </div>
                <Field label="First day in the U.S. in a non-F/J/M/Q status (if in 2025)" hint="e.g. your H-1B start date or your 2025 arrival date. Needed for dual-status returns.">
                  <TextInput type="date" value={prof.first_nonexempt_day} onChange={(v) => setP({ first_nonexempt_day: v })} /></Field>
              </div>
            )}
            <details className="card" open={!!residency && residency.status !== "resident"}>
              <summary className="cursor-pointer font-semibold text-sm">Details for Form 8843 / Schedule OI (nonresidents)</summary>
              <div className="grid sm:grid-cols-2 gap-4 mt-4">
                <Field label="Passport country"><TextInput value={prof.passport_country} onChange={(v) => setP({ passport_country: v })} placeholder={prof.country} /></Field>
                <Field label="Passport number"><TextInput value={prof.passport_number} onChange={(v) => setP({ passport_number: v })} /></Field>
                <Field label="Country of tax residence (if different)"><TextInput value={prof.tax_residence_country} onChange={(v) => setP({ tax_residence_country: v })} /></Field>
                <Field label="Date you entered the U.S. on this visa"><TextInput type="date" value={prof.visa_entry_date} onChange={(v) => setP({ visa_entry_date: v })} /></Field>
                <Field label="Previous visa (if it changed)"><TextInput value={prof.previous_visa} onChange={(v) => setP({ previous_visa: v })} placeholder="F-1" /></Field>
                <Field label="Months you claimed this treaty benefit before 2025"><MoneyInput integer value={prof.treaty_prior_months} onChange={(v) => setP({ treaty_prior_months: v })} /></Field>
                <Field label="School / institution"><TextInput value={tp.school} onChange={(v) => setT({ school: v })} /></Field>
                <Field label="School address & phone"><TextInput value={tp.school_address} onChange={(v) => setT({ school_address: v })} /></Field>
                <Field label="Program director (name, address, phone)" wide hint="Usually your international student office / DSO."><TextInput value={prof.program_director} onChange={(v) => setP({ program_director: v })} /></Field>
              </div>
              <div className="mt-4">
                <label className="lbl">Visa type in each earlier year (F, J, M or Q; blank if not in the U.S.)</label>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {[2019, 2020, 2021, 2022, 2023, 2024].map((y) => (
                    <div key={y}><span className="text-xs text-gray-500">{y}</span>
                      <TextInput value={prof.visa_by_year[String(y)] || ""} maxLength={6}
                        onChange={(v) => setP({ visa_by_year: { ...prof.visa_by_year, [String(y)]: v.toUpperCase() } })} /></div>
                  ))}
                </div>
              </div>
              <div className="mt-4">
                <Field label={`Every date you entered and left the U.S. in ${TAX_YEAR}`} hint="One trip per line: entered-date left-date (YYYY-MM-DD). Leave the left date empty if you are still here.">
                  <textarea className="inp" rows={3} value={tripsText} onChange={(e) => setTripsText(e.target.value)} placeholder={"2025-01-05 2025-05-20\n2025-08-15"} />
                </Field>
              </div>
              <div className="grid sm:grid-cols-2 gap-4 mt-4">
                <Field label="Ever applied for a green card?"><YesNo value={prof.applied_green_card ? "yes" : "no"} onChange={(v) => setP({ applied_green_card: v === "yes" })} /></Field>
                <Field label="Filed a U.S. tax return before?"><YesNo value={prof.filed_prior_return ? "yes" : "no"} onChange={(v) => setP({ filed_prior_return: v === "yes" })} /></Field>
                {prof.filed_prior_return && <Field label="Latest year and form filed"><TextInput value={prof.prior_return_info} onChange={(v) => setP({ prior_return_info: v })} placeholder="2024 1040-NR" /></Field>}
              </div>
            </details>
          </>
        )}
        {residency && (
          <div className="card border-l-4 border-l-formblue">
            <div className="font-mono text-[11px] tracking-wider text-gray-500 mb-1">DETERMINATION · TY {TAX_YEAR}</div>
            <div className="text-xl font-bold">{residency.label}</div>
            <div className="text-formblue font-semibold text-sm mb-2">
              Form {residency.form}{residency.form_8843_required ? " + Form 8843" : ""}
            </div>
            <p className="text-sm text-gray-600 leading-relaxed">{residency.explanation}</p>
            {residency.warnings?.map((w, i) => <p key={i} className="text-sm text-owe mt-2">⚠ {w}</p>)}
          </div>
        )}
      </div>
    </>
  );

  const stepInterview = (
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
              <p className="font-semibold mb-1">{q.text}</p>
              {q.help && <p className="text-xs text-gray-500 mb-3">{q.help}</p>}
              <div className="mt-2">
                {q.type === "yesno" && <YesNo value={answers[q.id] || ""} onChange={(v) => answer(q, v)} />}
                {q.type === "number" && (
                  <input key={q.id} className="inp max-w-[200px]" inputMode="numeric" defaultValue={answers[q.id] ?? ""}
                    onBlur={(e) => e.target.value !== "" && answer(q, e.target.value)}
                    onKeyDown={(e: any) => e.key === "Enter" && e.target.value !== "" && answer(q, e.target.value)} />
                )}
                {q.type === "select" && (
                  <select className="inp max-w-[280px]" value={answers[q.id] || ""} onChange={(e) => answer(q, e.target.value)}>
                    <option value="" disabled>Choose…</option>
                    {q.options?.map((o) => <option key={o}>{o}</option>)}
                  </select>
                )}
              </div>
            </div>
          ))}
          <p className="text-xs text-gray-500">You can skip questions — just continue and fill in the income step directly.</p>
        </div>
      )}
    </>
  );

  const stName = STATES.find(([c]) => c === inc.state)?.[1] || inc.state;
  const taxState = !NO_TAX.includes(inc.state);
  const stepIncome = (
    <>
      <h2 className="text-2xl font-bold mb-5">Income &amp; deductions</h2>

      <div className="card mb-5">
        <div className="font-mono text-[11px] text-formblue mb-3 tracking-wider">STATE RETURN</div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={`State you lived in (${TAX_YEAR})`}>
            <select className="inp" value={inc.state} onChange={(e) => setI({ state: e.target.value })}>
              {STATES.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
              <optgroup label="No state income tax">{NO_TAX.map((s) => <option key={s} value={s}>{s}</option>)}</optgroup>
            </select></Field>
          {taxState && <Field label={`Full-year ${stName} resident?`} hint={inc.state === "CA" ? "Students living in CA for the school year are usually CA residents, even if nonresident aliens federally." : "NY residency depends on domicile or 183+ days with a permanent place of abode."}>
            <YesNo value={inc.ca_full_year_resident ? "yes" : "no"} onChange={(v) => setI({ ca_full_year_resident: v === "yes" })} /></Field>}
          {taxState && !inc.ca_full_year_resident && (
            <Field label={`${stName}-source income ($)`} hint={`Income earned in ${stName} or while you lived there (wages for work done there, etc.).`}>
              <MoneyInput value={inc.state_source_income ?? 0} onChange={(v) => setI({ state_source_income: v })} /></Field>)}
          {inc.state === "CA" && <Field label="Rented your CA home for 6+ months?"><YesNo value={inc.ca_renter ? "yes" : "no"} onChange={(v) => setI({ ca_renter: v === "yes" })} /></Field>}
          {inc.state === "CA" && <Field label="Health coverage all of 2025?" hint="School insurance counts. Without it California may charge a penalty (Form 540 line 92) — not computed here.">
            <YesNo value={prof.health_coverage ? "yes" : "no"} onChange={async (v) => { setP({ health_coverage: v === "yes" });
              await apiJson(`/returns/${rid}/profile`, { method: "PUT", body: JSON.stringify({ ...prof, health_coverage: v === "yes", citizen: citAns === "yes", green_card: citAns === "no" && gcAns === "yes" }) }).catch(() => {}); }} /></Field>}
        </div>
      </div>

      <div className="card mb-5 border-dashed">
        <div className="font-mono text-[11px] text-formblue mb-2 tracking-wider">UPLOAD A DOCUMENT — W-2, 1099-INT, 1099-DIV, 1099-NEC</div>
        <p className="text-sm text-gray-500 mb-3">PDF, JPG, PNG or HEIC. We read the boxes; you review before anything is added. Always compare with your paper form.</p>
        <input type="file" accept=".pdf,.jpg,.jpeg,.png,.heic" className="text-sm"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); e.target.value = ""; }} />
        {ocr.busy && <p className="text-sm text-formblue mt-2">Reading document…</p>}
        {ocr.err && <p className="text-sm text-owe mt-2">{ocr.err}</p>}
        {ocr.doc && (
          <div className="mt-4 border-t border-rule pt-3">
            <div className="font-semibold text-sm mb-2">Detected: {ocr.doc.doc_type}
              {ocr.doc.extracted.needs_review && <span className="ml-2 text-xs font-mono text-owe">CHECK HIGHLIGHTED VALUES</span>}</div>
            <div className="grid sm:grid-cols-2 gap-2 mb-3">
              {Object.entries(ocr.doc.extracted.fields as Record<string, any>).map(([k, f]) => (
                <div key={k} className="text-sm flex justify-between gap-2 border-b border-dotted border-rule py-1">
                  <span className="text-gray-500">{k.replace(/_/g, " ")}</span>
                  <span className={`font-mono ${f.confidence < 0.8 ? "text-owe" : ""}`}>{typeof f.value === "number" ? f.value.toLocaleString() : f.value}</span>
                </div>
              ))}
            </div>
            <div className="flex gap-2 flex-wrap">
              {ocr.doc.doc_type !== "unknown" && <button className="btn" onClick={applyDoc}>Looks right — add to my return</button>}
              <button className="btn-ghost" onClick={() => setOcr({ busy: false, doc: null, err: "" })}>Discard — I&apos;ll type it</button>
            </div>
          </div>
        )}
      </div>

      {inc.w2s.map((w, i) => (
        <div key={i} className="card mb-4">
          <div className="flex justify-between items-center mb-3">
            <div className="font-mono text-[11px] text-formblue">W-2 #{i + 1}</div>
            {inc.w2s.length > 1 && <button className="text-xs text-owe" onClick={() => setI({ w2s: inc.w2s.filter((_, j) => j !== i) })}>Remove</button>}
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Employer"><TextInput value={w.employer} onChange={(v) => setW2(i, { employer: v })} /></Field>
            <Field label="Employer EIN (box b)"><TextInput value={w.ein} onChange={(v) => setW2(i, { ein: v })} placeholder="12-3456789" /></Field>
            <Field label="Box 1 — wages"><MoneyInput value={w.wages} onChange={(v) => setW2(i, { wages: v })} /></Field>
            <Field label="Box 2 — federal tax withheld"><MoneyInput value={w.fed_withholding} onChange={(v) => setW2(i, { fed_withholding: v })} /></Field>
            <Field label="Box 4 — Social Security tax"><MoneyInput value={w.ss_tax} onChange={(v) => setW2(i, { ss_tax: v })} /></Field>
            <Field label="Box 6 — Medicare tax"><MoneyInput value={w.medicare_tax} onChange={(v) => setW2(i, { medicare_tax: v })} /></Field>
            <Field label="Box 15 — state"><TextInput value={w.state} onChange={(v) => setW2(i, { state: v.toUpperCase().slice(0, 2) })} placeholder={inc.state} /></Field>
            <Field label="Box 17 — state tax withheld"><MoneyInput value={w.state_withholding} onChange={(v) => setW2(i, { state_withholding: v })} /></Field>
          </div>
        </div>
      ))}
      <button className="btn-ghost mb-6" onClick={() => setI({ w2s: [...inc.w2s, emptyW2(inc.state)] })}>+ Add another W-2</button>

      <div className="grid sm:grid-cols-2 gap-4">
        {isDual && <Field label="Wages earned before your residency start date" hint={`Part of box 1 earned before ${residency?.residency_start}. Treaty benefits apply only to this part.`}>
          <MoneyInput value={inc.wages_nr_period} onChange={(v) => setI({ wages_nr_period: v })} /></Field>}
        {(yes("has_1042s") || inc.comp_1042s > 0 || inc.scholarship_1042s > 0) && (
          <>
            <Field label="1042-S: treaty-exempt pay (codes 17-20, box 2)"><MoneyInput value={inc.comp_1042s} onChange={(v) => setI({ comp_1042s: v })} /></Field>
            <Field label="1042-S: scholarship/fellowship (code 16, box 2)"><MoneyInput value={inc.scholarship_1042s} onChange={(v) => setI({ scholarship_1042s: v })} /></Field>
            <Field label="1042-S: federal tax withheld (box 7a)"><MoneyInput value={inc.withholding_1042s} onChange={(v) => setI({ withholding_1042s: v })} /></Field>
          </>)}
        {(yes("has_scholarship") || inc.scholarship_taxable > 0) && (
          <Field label="Taxable scholarship not on W-2 / 1042-S" hint="Grants used for rent, food or travel (not tuition, fees, books).">
            <MoneyInput value={inc.scholarship_taxable} onChange={(v) => setI({ scholarship_taxable: v })} /></Field>)}
        {(yes("has_tips_overtime") || inc.qualified_tips > 0 || inc.qualified_overtime > 0) && (
          <>
            <Field label="Qualified tips (Schedule 1-A)" hint="Requires an SSN valid for work. Not allowed if married filing separately."><MoneyInput value={inc.qualified_tips} onChange={(v) => setI({ qualified_tips: v })} /></Field>
            <Field label="Qualified overtime premium (the extra 0.5x only)"><MoneyInput value={inc.qualified_overtime} onChange={(v) => setI({ qualified_overtime: v })} /></Field>
          </>)}
        {(yes("has_interest") || inc.interest > 0) && (
          <Field label="Interest income (1099-INT box 1)" hint={isNRA ? "Not taxable federally for nonresident aliens, but taxable for state residents." : undefined}>
            <MoneyInput value={inc.interest} onChange={(v) => setI({ interest: v })} /></Field>)}
        {(yes("has_dividends") || inc.dividends > 0) && (
          <>
            <Field label="Ordinary dividends (1099-DIV 1a / 1042-S code 06)"><MoneyInput value={inc.dividends} onChange={(v) => setI({ dividends: v })} /></Field>
            {!isNRA && <Field label="Qualified dividends (1099-DIV 1b)"><MoneyInput value={inc.qualified_dividends} onChange={(v) => setI({ qualified_dividends: v })} /></Field>}
          </>)}
        {(yes("has_capital_gains") || inc.capital_gain_lt !== 0 || inc.capital_gain_st !== 0) && (
          <>
            <Field label="Net short-term gain or (loss)" hint="Held 1 year or less. Use a minus sign for a loss."><MoneyInput allowNegative value={inc.capital_gain_st} onChange={(v) => setI({ capital_gain_st: v })} /></Field>
            <Field label="Net long-term gain or (loss)"><MoneyInput allowNegative value={inc.capital_gain_lt} onChange={(v) => setI({ capital_gain_lt: v })} /></Field>
          </>)}
        {(yes("has_self_employment") || inc.se_income !== 0) && (
          <Field label="Self-employment net profit (after expenses)"><MoneyInput allowNegative value={inc.se_income} onChange={(v) => setI({ se_income: v })} /></Field>)}
        {(yes("has_interest") || yes("has_dividends") || yes("has_self_employment") || inc.withholding_1099 > 0) && (
          <Field label="Federal tax withheld on 1099s"><MoneyInput value={inc.withholding_1099} onChange={(v) => setI({ withholding_1099: v })} /></Field>)}
        {(yes("student_loan") || inc.student_loan_interest > 0) && (
          <Field label="Student loan interest (1098-E)"><MoneyInput value={inc.student_loan_interest} onChange={(v) => setI({ student_loan_interest: v })} /></Field>)}
        {isResident && (yes("tuition_paid") || inc.tuition_paid > 0) && (
          <>
            <Field label="Qualified tuition & fees paid (1098-T)"><MoneyInput value={inc.tuition_paid} onChange={(v) => setI({ tuition_paid: v })} /></Field>
            <Field label="Education credit">
              <select className="inp" value={inc.education_credit_type} onChange={(e) => setI({ education_credit_type: e.target.value })}>
                <option value="none">None</option><option value="aotc">American Opportunity (first 4 years of college)</option><option value="llc">Lifetime Learning</option>
              </select></Field>
          </>)}
        {(yes("has_charity") || inc.charitable > 0) && (
          <Field label="Gifts to U.S. charities"><MoneyInput value={inc.charitable} onChange={(v) => setI({ charitable: v })} /></Field>)}
        <Field label="Other state income tax paid" hint="Besides W-2 box 17 (e.g. a prior-year balance paid in 2025). Used as an itemized deduction.">
          <MoneyInput value={inc.state_tax_other} onChange={(v) => setI({ state_tax_other: v })} /></Field>
        {isResident && <Field label="Other itemized deductions" hint="Mortgage interest, etc. We compare with the standard deduction.">
          <MoneyInput value={inc.other_itemized} onChange={(v) => setI({ other_itemized: v })} /></Field>}
        <Field label="2025 estimated tax payments"><MoneyInput value={inc.estimated_payments} onChange={(v) => setI({ estimated_payments: v })} /></Field>
        {isResident && inc.qualifying_children === 0 && (
          <Field label="Your age on Dec 31, 2025" hint="Earned income credit without children requires age 25-64.">
            <MoneyInput integer value={inc.age} onChange={(v) => setI({ age: v })} /></Field>)}
      </div>
    </>
  );

  const F = result?.federal, C = result?.state;
  const stepResults = !result ? <p className="text-gray-500">Calculating…</p> : (
    <>
      <h2 className="text-2xl font-bold mb-5">Your {TAX_YEAR} results</h2>
      <div className="grid sm:grid-cols-2 gap-4 mb-6">
        {[{ t: "Federal", f: F!.form, r: F!.lines.refund },
          ...(C!.form === "none" ? [] : [{ t: STATES.find(([c]) => c === C!.state)?.[1] || C!.state, f: C!.form, r: C!.lines.refund }])].map((x) => (
          <div key={x.t} className="card border-t-4" style={{ borderTopColor: x.r >= 0 ? GREEN : RED }}>
            <div className="lbl mb-0">{x.t} · Form {x.f}</div>
            <div className="font-mono text-3xl font-bold my-1" style={{ color: x.r >= 0 ? GREEN : RED }}>${Math.abs(x.r).toLocaleString()}</div>
            <div className="text-sm text-gray-500">{x.r >= 0 ? "Refund" : "Amount you owe"}</div>
          </div>
        ))}
      </div>
      {[...(F!.warnings || []), ...(C!.warnings || [])].length > 0 && (
        <div className="card mb-6 border-l-4" style={{ borderLeftColor: RED }}>
          <h3 className="font-bold mb-2">Please review</h3>
          {[...(F!.warnings || []), ...(C!.warnings || [])].map((w, i) => <p key={i} className="text-sm text-gray-700 mb-1">⚠ {w}</p>)}
        </div>
      )}
      <button className="btn w-full sm:w-auto mb-2" disabled={busy} onClick={async () => {
        setBusy(true); setErr("");
        try { await downloadPackage(rid, TAX_YEAR); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
      }}>{busy ? "Preparing…" : "Download filing package (PDF)"}</button>
      <p className="text-xs text-gray-500 mb-8">Draft official forms for synthetic testing. Do not sign or file this preview; tax coverage and correctness review remain incomplete.</p>
      <h3 className="font-bold mb-2">How your tax was calculated</h3>
      <div className="card mb-6 space-y-2">
        {[...F!.explanations, ...C!.explanations].map((e, i) => <p key={i} className="text-sm text-gray-600">• {e}</p>)}
      </div>
      <h3 className="font-bold mb-2">Filing checklist</h3>
      <div className="card mb-6">
        {result.checklist.map((c, i) => (
          <div key={i} className="flex gap-2.5 py-2 border-b border-dotted border-rule last:border-0 text-sm">
            <span className="font-mono text-formblue">☐</span>{c}
          </div>
        ))}
      </div>
      <h3 className="font-bold mb-2">Where to mail</h3>
      <div className="card text-sm space-y-2">
        {result.mailing?.federal && <p><b>Federal:</b> {result.mailing.federal}</p>}
        {result.mailing?.state && <p><b>{C!.state}:</b> {result.mailing.state}</p>}
        <p className="text-gray-500">Deadline: April 15, 2026 (June 15, 2026 for nonresident aliens with no wages subject to withholding). Form 8843 alone is due June 15, 2026.</p>
      </div>
    </>
  );

  const body = [stepAbout, stepResidency, stepInterview, stepIncome, stepResults][step];

  return (
    <div className="max-w-[1060px] mx-auto px-5 pb-24 lg:pb-14">
      <div className="flex gap-1 flex-wrap pt-4">
        {STEPS.map((s, i) => (
          <button key={s} onClick={() => (i < step || (i === 4 && result)) && setStep(i)}
            className={`px-3 py-1.5 text-xs font-mono rounded ${i === step ? "bg-formblue text-white font-bold" : i < step ? "text-formblue" : "text-gray-400"}`}>
            {i + 1} {s}
          </button>
        ))}
        <a href="/dashboard" className="ml-auto px-3 py-1.5 text-xs font-mono text-gray-500">← All returns</a>
      </div>
      <div className="flex gap-6 items-start pt-5">
        <main className="flex-1 min-w-0">
          {body}
          {err && <p className="text-sm text-owe mt-4">{err}</p>}
          {step < 4 && (
            <div className="flex gap-3 mt-8">
              {step > 0 && <button className="btn-ghost" onClick={() => { setErr(""); setStep(step - 1); }}>Back</button>}
              <button className="btn" onClick={next} disabled={busy}>
                {busy ? "Working…" : step === 3 ? "Calculate my return" : "Save & continue"}
              </button>
            </div>
          )}
          {step === 4 && <button className="btn-ghost mt-8" onClick={() => setStep(3)}>Edit income</button>}
        </main>
        <Ledger result={result} />
      </div>
    </div>
  );
}
