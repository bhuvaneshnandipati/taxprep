"use client";
import { useState } from "react";

const fmt = (n: number) => (n < 0 ? "−$" : "$") + Math.abs(Math.round(n)).toLocaleString();

export type CalcResult = {
  residency: { label: string; form: string; form_8843_required: boolean; explanation: string };
  federal: { form: string; lines: Record<string, number>; explanations: string[] };
  state: { state?: string; form: string; lines: Record<string, number>; explanations: string[] };
  checklist: string[];
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

export default function Ledger({ result }: { result: CalcResult }) {
  const [open, setOpen] = useState(false);
  if (!result) return (
    <aside className="hidden lg:block w-[300px] shrink-0 card sticky top-5 text-sm text-gray-500">
      <div className="font-mono text-[11px] tracking-wider mb-2">FORM LEDGER</div>
      Answers post to real form lines here after you calculate.
    </aside>
  );
  const F = result.federal.lines, C = result.state.lines;
  const body = (
    <>
      <div className="font-mono text-[11px] tracking-wider text-gray-500 mb-2">FORM {result.federal.form} · TY 2025</div>
      <Row line="1a" desc="Wages" val={F["1a_wages"]} />
      {F["2b_interest"] > 0 && <Row line="2b" desc="Taxable interest" val={F["2b_interest"]} />}
      {F["3b_dividends"] > 0 && <Row line="3b" desc="Dividends" val={F["3b_dividends"]} />}
      <Row line="11" desc="Adjusted gross income" val={F["11_agi"]} strong />
      <Row line="12" desc="Deduction" val={-F["12_deduction"]} />
      <Row line="15" desc="Taxable income" val={F["15_taxable_income"]} strong />
      <Row line="16" desc="Tax" val={F["16_tax"]} />
      {F["19_ctc_odc"] > 0 && <Row line="19" desc="Child tax credit / ODC" val={-F["19_ctc_odc"]} />}
      <Row line="24" desc="Total tax" val={F["24_total_tax"]} strong />
      <Row line="33" desc="Total payments" val={F["33_total_payments"]} />
      <Row line={F.refund >= 0 ? "34" : "37"} desc={F.refund >= 0 ? "Federal refund" : "Federal owed"}
           val={Math.abs(F.refund)} strong color={F.refund >= 0 ? "#1E7A4D" : "#B3382C"} />
      {result.state.form !== "none" && (
        <>
          <div className="font-mono text-[11px] tracking-wider text-gray-500 mt-4 mb-2">
            {result.state.state || "CA"} {result.state.form}
          </div>
          <Row line="TI" desc="State taxable income" val={C["19_taxable"] ?? C["37_taxable"] ?? 0} strong />
          <Row line="TAX" desc="State total tax" val={C["64_total_tax"] ?? C["46_total_tax"] ?? 0} />
          <Row line="=" desc={C.refund >= 0 ? "State refund" : "State owed"}
               val={Math.abs(C.refund)} strong color={C.refund >= 0 ? "#1E7A4D" : "#B3382C"} />
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
          <span>FED {F.refund >= 0 ? "REFUND" : "OWED"} {fmt(Math.abs(F.refund))}{result.state.form !== "none" ? ` · ${result.state.state || "CA"} ${fmt(Math.abs(C.refund))}` : ""}</span>
          <span>{open ? "▾ hide" : "▴ form lines"}</span>
        </button>
        {open && <div className="bg-white border-t-[1.5px] border-rule p-4 max-h-[55vh] overflow-y-auto">{body}</div>}
      </div>
    </>
  );
}
