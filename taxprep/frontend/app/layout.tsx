import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TaxPrep — Tax returns for international students",
  description: "Prepare your U.S. federal (1040 / 1040-NR / 8843) and California or New York income tax return.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="bg-white border-b-[1.5px] border-rule px-5 py-3.5 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <a href="/dashboard" className="font-bold text-lg tracking-tight">TaxPrep</a>
          <span className="font-mono text-[11px] text-gray-500">TAX YEAR 2025 · FEDERAL + CA / NY</span>
        </header>
        <p className="mx-auto max-w-5xl px-5 pt-4 text-sm" role="note">Preview for synthetic test data only. Tax coverage and security review are incomplete. Do not enter real taxpayer information or file generated forms.</p>
        {children}
      </body>
    </html>
  );
}
