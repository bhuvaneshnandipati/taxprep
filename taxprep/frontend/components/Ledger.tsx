"use client";
import { useState } from "react";

const fmt = (n: number | undefined) => {
  const v = Math.round(n || 0);
  return (v < 0 ? "−$" : "$") + Math.abs(v).toLocaleString();
};

export type Residency = {
  status: string; label: string; form: string; form_8843_required: boolean; explanation: string;
  residency_start?: string; warnings?: string[]; weighted_days?: number;
};
export type CalcResult = {
  residency: Residency;
  federal: { form: string; mode: string; filing_status: string; lines: Record<string, any>;
             explanations: string[]; warnings: string[]; schedules: string[]; treaty: any };
  state: { state: string; form: string; lines: Record<string, any>; explanations: string[]; warnings?: string[] };
  checklist: string[];
  mailing: { federal?: string; state?: string };
} | null;

function Row({ line, desc, val, strong, color }:
  { line: string; desc: string; val: number; strong?: boolean; color?: string }) {
  return (
    <div className="flex items-baseline gap-2 py-1 border-b border-dotted border-rule">
      <span className="font-mono text-[11px] text-formblue min-w-[34px]">{line}</span>
      <span className={`text-xs flex-1 ${strong ? "font-semibold text-ink" : "text-gray-500"}`}>{desc}</span>
      <span className={`font-mono text-[13px] ${strong ? "font-bold" : ""}`} style={color ? { color } : {}}>{fmt(val)}</span>
    </div>
  );
}

export const GREEN = "#1E7A4D", RED = "#B3382C";

export default function Ledger({ result }: { result: CalcResult }) {
  const [open, setOpen] = useState(false);
  if (!result) return (
    <aside className="hidden lg:block w-[300px] shrink-0 card sticky top-5 text-sm text-gray-500">
      <div className="font-mono text-[11px] tracking-wider mb-2">FORM LEDGER</div>
      Your numbers post to the real form lines here after you calculate.
    </aside>
  );
  const F = result.federal.lines, C = result.state.lines;
  const nr = result.federal.form === "1040-NR";
  const body = (
    <>
      <div className="font-mono text-[11px] tracking-wider text-gray-500 mb-2">FORM {result.federal.form} · TY 2025</div>
      <Row line="1a" desc="Wages (W-2 box 1)" val={F.wages} />
      {nr && F.treaty_exempt_income > 0 && <Row line="1k" desc="Treaty-exempt income" val={F.treaty_exempt_income} />}
      {F.taxable_interest > 0 && <Row line="2b" desc="Taxable interest" val={F.taxable_interest} />}
      {F.ordinary_dividends > 0 && <Row line="3b" desc="Dividends" val={F.ordinary_dividends} />}
      {F.capital_gain !== 0 && <Row line="7" desc="Capital gain or (loss)" val={F.capital_gain} />}
      {F.other_income > 0 && <Row line="8" desc="Schedule 1 income" val={F.other_income} />}
      {F.adjustments > 0 && <Row line="10" desc="Adjustments" val={-F.adjustments} />}
      <Row line="11" desc="Adjusted gross income" val={F.agi} strong />
      <Row line="12" desc={`${F.deduction_type === "standard" ? "Standard" : "Itemized"} deduction`} val={-F.deduction} />
      {F.sched1a_total > 0 && <Row line={nr ? "13c" : "13b"} desc="Tips / overtime (Sch. 1-A)" val={-F.sched1a_total} />}
      <Row line="15" desc="Taxable income" val={F.taxable_income} strong />
      <Row line="16" desc="Tax" val={F.tax} />
      {F.ctc_odc > 0 && <Row line="19" desc="Child tax credit / ODC" val={-F.ctc_odc} />}
      {F.education_credit > 0 && <Row line="20" desc="Education credit" val={-F.education_credit} />}
      {F.other_taxes > 0 && <Row line="23" desc="Other taxes" val={F.other_taxes} />}
      {F.nec_tax > 0 && <Row line="23a" desc="Tax on non-ECI (Sch. NEC)" val={F.nec_tax} />}
      <Row line="24" desc="Total tax" val={F.total_tax} strong />
      <Row line="25" desc="Federal tax withheld" val={F.withholding_total} />
      {F.eitc > 0 && <Row line="27" desc="Earned income credit" val={F.eitc} />}
      {F.actc > 0 && <Row line="28" desc="Additional child tax credit" val={F.actc} />}
      {F.aotc_refundable > 0 && <Row line="29" desc="American opportunity credit" val={F.aotc_refundable} />}
      <Row line="33" desc="Total payments" val={F.total_payments} />
      <Row line={F.refund >= 0 ? "34" : "37"} desc={F.refund >= 0 ? "Federal refund" : "Federal amount owed"}
           val={Math.abs(F.refund)} strong color={F.refund >= 0 ? GREEN : RED} />
      {result.state.form !== "none" && (
        <>
          <div className="font-mono text-[11px] tracking-wider text-gray-500 mt-4 mb-2">
            {result.state.state} {result.state.form}
          </div>
          <Row line="AGI" desc="State AGI" val={C.ca_agi ?? C.ny_agi ?? 0} />
          <Row line="TI" desc="State taxable income" val={C.taxable_income ?? 0} strong />
          <Row line="TAX" desc="State total tax" val={C.total_tax ?? 0} />
          <Row line="W/H" desc="State tax withheld" val={C.withholding ?? 0} />
          <Row line="=" desc={C.refund >= 0 ? "State refund" : "State amount owed"}
               val={Math.abs(C.refund)} strong color={C.refund >= 0 ? GREEN : RED} />
        </>
      )}
    </>
  );
  return (
    <>
      <aside className="hidden lg:block w-[300px] shrink-0 card sticky top-5">{body}</aside>
      <div className="lg:hidden fixed bottom-0 inset-x-0 z-50">
        <button onClick={() => setOpen(!open)}
          className="w-full px-4 py-3 bg-ink text-white flex justify-between items-center font-mono text-[13px]">
          <span>FED {F.refund >= 0 ? "REFUND" : "OWED"} {fmt(Math.abs(F.refund))}{result.state.form !== "none" ? ` · ${result.state.state} ${fmt(Math.abs(C.refund))}` : ""}</span>
          <span>{open ? "▾ hide" : "▴ form lines"}</span>
        </button>
        {open && <div className="bg-white border-t-[1.5px] border-rule p-4 max-h-[55vh] overflow-y-auto">{body}</div>}
      </div>
    </>
  );
}
