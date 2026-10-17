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
        {children}
      </body>
    </html>
  );
}
