"use client";
/* Detail editors for the official forms: dependents (Form 1040 + Schedule 8812), payers
   (Schedule B), foreign accounts (Schedule B Part III), 1099-B totals (Schedule D) and a
   business (Schedule C). Kept at module level so inputs keep focus while typing. */
import { Field, MoneyInput, TextInput, YesNo } from "./Fields";

export type Dependent = { first_name: string; last_name: string; ssn: string; relationship: string;
  lived_with_you: boolean; lived_in_us: boolean; full_time_student: boolean; disabled: boolean; credit: "ctc" | "odc" | "none" };
export type Payer = { name: string; amount: number };
export type Business = { description: string; code: string; name: string; ein: string; gross_receipts: number; returns: number;
  advertising: number; car_truck: number; commissions: number; contract_labor: number; insurance: number;
  legal_professional: number; office: number; supplies: number; taxes_licenses: number; travel: number;
  meals_total: number; utilities: number; other_expenses: number; other_description: string };

export const emptyDependent = (): Dependent => ({ first_name: "", last_name: "", ssn: "", relationship: "",
  lived_with_you: true, lived_in_us: true, full_time_student: false, disabled: false, credit: "ctc" });
export const emptyBusiness = (): Business => ({ description: "", code: "", name: "", ein: "", gross_receipts: 0, returns: 0,
  advertising: 0, car_truck: 0, commissions: 0, contract_labor: 0, insurance: 0, legal_professional: 0, office: 0,
  supplies: 0, taxes_licenses: 0, travel: 0, meals_total: 0, utilities: 0, other_expenses: 0, other_description: "" });

function Check({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm cursor-pointer">
      <input type="checkbox" className="w-4 h-4 accent-formblue" checked={value} onChange={(e) => onChange(e.target.checked)} />{label}
    </label>
  );
}

export function DependentsEditor({ value, onChange }: { value: Dependent[]; onChange: (v: Dependent[]) => void }) {
  const set = (i: number, p: Partial<Dependent>) => onChange(value.map((d, j) => (j === i ? { ...d, ...p } : d)));
  return (
    <div className="sm:col-span-2">
      <h3 className="font-bold mb-1">Dependents</h3>
      <p className="text-xs text-mute mb-3">Children and relatives you support. Their names and SSNs go on Form 1040; credits are figured on Schedule 8812.</p>
      {value.map((d, i) => (
        <div key={i} className="card mb-3 grid sm:grid-cols-2 gap-4">
          <Field label="First name"><TextInput value={d.first_name} onChange={(v) => set(i, { first_name: v })} maxLength={40} /></Field>
          <Field label="Last name"><TextInput value={d.last_name} onChange={(v) => set(i, { last_name: v })} maxLength={40} /></Field>
          <Field label="SSN / ITIN / ATIN"><TextInput value={d.ssn} onChange={(v) => set(i, { ssn: v })} placeholder="XXX-XX-XXXX" maxLength={11} /></Field>
          <Field label="Relationship"><TextInput value={d.relationship} onChange={(v) => set(i, { relationship: v })} placeholder="Son, Daughter, Parent…" maxLength={30} /></Field>
          <Field label="Credit" hint="Child tax credit: under 17 at year end with an SSN valid for work. Otherwise usually the $500 credit for other dependents." wide>
            <select className="inp" value={d.credit} onChange={(e) => set(i, { credit: e.target.value as Dependent["credit"] })}>
              <option value="ctc">Child tax credit (under 17, has SSN)</option>
              <option value="odc">Credit for other dependents</option>
              <option value="none">No credit</option>
            </select></Field>
          <div className="sm:col-span-2 flex flex-wrap gap-x-6 gap-y-2">
            <Check label="Lived with me more than half of 2025" value={d.lived_with_you} onChange={(v) => set(i, { lived_with_you: v })} />
            <Check label="…and in the U.S." value={d.lived_in_us} onChange={(v) => set(i, { lived_in_us: v })} />
            <Check label="Full-time student" value={d.full_time_student} onChange={(v) => set(i, { full_time_student: v })} />
            <Check label="Permanently and totally disabled" value={d.disabled} onChange={(v) => set(i, { disabled: v })} />
          </div>
          <button type="button" className="text-xs text-owe justify-self-start" onClick={() => onChange(value.filter((_, j) => j !== i))}>Remove dependent</button>
        </div>
      ))}
      <button type="button" className="btn-ghost" onClick={() => onChange([...value, emptyDependent()])}>+ Add dependent</button>
    </div>
  );
}

export function PayersEditor({ title, hint, value, onChange, max }: { title: string; hint: string; value: Payer[]; onChange: (v: Payer[]) => void; max: number }) {
  const set = (i: number, p: Partial<Payer>) => onChange(value.map((d, j) => (j === i ? { ...d, ...p } : d)));
  const total = value.reduce((a, p) => a + (p.amount || 0), 0);
  return (
    <div className="sm:col-span-2">
      <div className="lbl">{title}</div>
      <p className="text-xs text-mute mb-2">{hint}</p>
      {value.map((p, i) => (
        <div key={i} className="flex gap-2 mb-2 items-center">
          <div className="flex-1"><TextInput value={p.name} onChange={(v) => set(i, { name: v })} placeholder="Payer name (bank, broker)" maxLength={60} /></div>
          <div className="w-36"><MoneyInput value={p.amount} onChange={(v) => set(i, { amount: v })} /></div>
          <button type="button" aria-label="Remove payer" className="text-owe px-2" onClick={() => onChange(value.filter((_, j) => j !== i))}>×</button>
        </div>
      ))}
      <div className="flex items-center justify-between">
        {value.length < max && <button type="button" className="text-sm text-formblue" onClick={() => onChange([...value, { name: "", amount: 0 }])}>+ Add payer</button>}
        {value.length > 0 && <span className="font-mono text-sm">Total ${total.toLocaleString()}</span>}
      </div>
    </div>
  );
}

export function ForeignAccounts({ inc, setI }: { inc: any; setI: (p: any) => void }) {
  return (
    <div className="sm:col-span-2 card bg-markersoft/40">
      <Field label="At any time in 2025, did you have a bank, brokerage or other financial account in a foreign country?"
        hint="Includes accounts in your home country (e.g. an Indian savings or NRO account). This is Schedule B line 7a; answering it is required when Schedule B is filed.">
        <YesNo value={inc.foreign_accounts ? "yes" : "no"} onChange={(v) => setI({ foreign_accounts: v === "yes" })} /></Field>
      {inc.foreign_accounts && (
        <div className="grid sm:grid-cols-2 gap-4 mt-4">
          <Field label="Country or countries"><TextInput value={inc.foreign_account_countries} onChange={(v) => setI({ foreign_account_countries: v })} placeholder="India" maxLength={120} /></Field>
          <Field label="Did the accounts together exceed $10,000 at any time in 2025?" hint="If yes, you must also file FinCEN Form 114 (FBAR) online at bsaefiling.fincen.gov by April 15 (automatic extension to October 15). It is separate from your tax return.">
            <YesNo value={inc.fbar_required ? "yes" : "no"} onChange={(v) => setI({ fbar_required: v === "yes" })} /></Field>
        </div>
      )}
      <div className="mt-4"><Field label="Did you receive a distribution from, or were you the grantor of or transferor to, a foreign trust?">
        <YesNo value={inc.foreign_trust ? "yes" : "no"} onChange={(v) => setI({ foreign_trust: v === "yes" })} /></Field></div>
    </div>
  );
}

export function BrokerTotals({ inc, setI }: { inc: any; setI: (p: any) => void }) {
  return (
    <div className="sm:col-span-2">
      <h3 className="font-bold mb-1">Stock and crypto sales (Form 1099-B)</h3>
      <p className="text-xs text-mute mb-3">Enter your broker&apos;s totals for sales where cost basis was reported to the IRS and there are no adjustments (Box A short-term, Box D long-term). Other sales need Form 8949, which TaxPrep does not prepare yet.</p>
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="Short-term proceeds"><MoneyInput value={inc.st_proceeds} onChange={(v) => setI({ st_proceeds: v })} /></Field>
        <Field label="Short-term cost basis"><MoneyInput value={inc.st_basis} onChange={(v) => setI({ st_basis: v })} /></Field>
        <Field label="Long-term proceeds"><MoneyInput value={inc.lt_proceeds} onChange={(v) => setI({ lt_proceeds: v })} /></Field>
        <Field label="Long-term cost basis"><MoneyInput value={inc.lt_basis} onChange={(v) => setI({ lt_basis: v })} /></Field>
        <Field label="Short-term loss carryover from 2024" hint="From last year's Capital Loss Carryover Worksheet. Leave 0 if none."><MoneyInput value={inc.st_loss_carryover} onChange={(v) => setI({ st_loss_carryover: v })} /></Field>
        <Field label="Long-term loss carryover from 2024"><MoneyInput value={inc.lt_loss_carryover} onChange={(v) => setI({ lt_loss_carryover: v })} /></Field>
      </div>
    </div>
  );
}

const EXPENSES: [keyof Business, string][] = [["advertising", "Advertising (8)"], ["car_truck", "Car and truck (9)"],
  ["commissions", "Commissions and fees (10)"], ["contract_labor", "Contract labor (11)"], ["insurance", "Insurance (15)"],
  ["legal_professional", "Legal and professional (17)"], ["office", "Office expense (18)"], ["supplies", "Supplies (22)"],
  ["taxes_licenses", "Taxes and licenses (23)"], ["travel", "Travel (24a)"], ["meals_total", "Business meals — full amount (24b; 50% is deducted)"],
  ["utilities", "Utilities (25)"], ["other_expenses", "Other expenses (Part V)"]];

export function BusinessEditor({ value, onChange }: { value: Business | null; onChange: (v: Business | null) => void }) {
  if (!value) return (
    <div className="sm:col-span-2"><button type="button" className="btn-ghost" onClick={() => onChange(emptyBusiness())}>+ Add self-employment / 1099-NEC business (Schedule C)</button></div>
  );
  const set = (p: Partial<Business>) => onChange({ ...value, ...p });
  const expenses = EXPENSES.reduce((a, [k]) => a + (k === "meals_total" ? (value.meals_total || 0) / 2 : (value[k] as number) || 0), 0);
  const profit = (value.gross_receipts || 0) - (value.returns || 0) - expenses;
  return (
    <div className="sm:col-span-2 card">
      <div className="flex justify-between items-baseline mb-3"><h3 className="font-bold">Business (Schedule C)</h3>
        <button type="button" className="text-xs text-owe" onClick={() => onChange(null)}>Remove</button></div>
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="What you do (A)"><TextInput value={value.description} onChange={(v) => set({ description: v })} placeholder="Software consulting" maxLength={60} /></Field>
        <Field label="Business code (B)" hint="6 digits from the Schedule C instructions, e.g. 541510 for computer programming services."><TextInput value={value.code} onChange={(v) => set({ code: v.replace(/\D/g, "").slice(0, 6) })} maxLength={6} /></Field>
        <Field label="Business name (C, optional)"><TextInput value={value.name} onChange={(v) => set({ name: v })} maxLength={60} /></Field>
        <Field label="EIN (D, optional)"><TextInput value={value.ein} onChange={(v) => set({ ein: v })} maxLength={10} /></Field>
        <Field label="Gross receipts (1099-NEC box 1 + other)"><MoneyInput value={value.gross_receipts} onChange={(v) => set({ gross_receipts: v })} /></Field>
        <Field label="Returns and allowances"><MoneyInput value={value.returns} onChange={(v) => set({ returns: v })} /></Field>
        {EXPENSES.map(([k, label]) => (
          <Field key={k} label={label}><MoneyInput value={value[k] as number} onChange={(v) => set({ [k]: v } as Partial<Business>)} /></Field>
        ))}
        {value.other_expenses > 0 && <Field label="Describe other expenses"><TextInput value={value.other_description} onChange={(v) => set({ other_description: v })} placeholder="Software subscriptions" maxLength={60} /></Field>}
      </div>
      <p className="mt-4 font-mono text-sm">Net profit (line 31): <span className={profit >= 0 ? "text-refund" : "text-owe"}>${Math.round(profit).toLocaleString()}</span></p>
    </div>
  );
}
