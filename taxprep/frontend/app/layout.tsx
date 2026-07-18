import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TaxPrep — Federal + California Tax Preparation",
  description: "Prepare your U.S. federal and California income tax return.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="bg-white border-b-[1.5px] border-rule px-5 py-3.5 flex items-baseline gap-3">
          <a href="/dashboard" className="font-bold text-lg tracking-tight">TaxPrep</a>
          <span className="font-mono text-[11px] text-gray-500">TAX YEAR 2025 · FEDERAL + CALIFORNIA</span>
        </header>
        {children}
      </body>
    </html>
  );
}
