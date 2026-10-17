"use client";
import { useEffect, useState } from "react";

/* Input components live at module level so React keeps the same element between renders
   (defining them inside a component re-mounts the <input> on every keystroke and drops focus). */

export function MoneyInput({ value, onChange, allowNegative = false, placeholder = "0", integer = false }: {
  value: number | null | undefined; onChange: (v: number) => void; allowNegative?: boolean;
  placeholder?: string; integer?: boolean;
}) {
  const [text, setText] = useState(value ? String(value) : "");
  // sync when the parent value changes from outside (resume, OCR apply)
  useEffect(() => {
    const parsed = parse(text);
    if ((value || 0) !== parsed) setText(value ? String(value) : "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  function parse(t: string) {
    const n = Number(t.replace(/[$,\s]/g, ""));
    return Number.isFinite(n) ? n : 0;
  }
  const pattern = integer ? (allowNegative ? /^-?\d*$/ : /^\d*$/)
    : (allowNegative ? /^-?[\d,]*\.?\d{0,2}$/ : /^[\d,]*\.?\d{0,2}$/);
  return (
    <input className="inp" inputMode={integer ? "numeric" : "decimal"} value={text} placeholder={placeholder}
      onChange={(e) => {
        const t = e.target.value.replace(/\$/g, "");
        if (t !== "" && !pattern.test(t)) return;
        setText(t);
        onChange(parse(t));
      }} />
  );
}

export function YesNo({ value, onChange }: { value: string; onChange: (v: "yes" | "no") => void }) {
  return (
    <div className="flex gap-2">
      {(["yes", "no"] as const).map((o) => (
        <button type="button" key={o} className={`chip ${value === o ? "chip-on" : "chip-off"}`} onClick={() => onChange(o)}>
          {o === "yes" ? "Yes" : "No"}
        </button>
      ))}
    </div>
  );
}

export function Field({ label, hint, children, wide }: { label: string; hint?: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className={wide ? "sm:col-span-2" : ""}>
      <label className="lbl">{label}</label>
      {children}
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}

export function TextInput({ value, onChange, placeholder, type = "text", maxLength }: {
  value: string; onChange: (v: string) => void; placeholder?: string; type?: string; maxLength?: number;
}) {
  return <input className="inp" type={type} value={value} placeholder={placeholder} maxLength={maxLength}
    onChange={(e) => onChange(e.target.value)} />;
}
