import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TaxPrep — Tax returns for international students",
  description: "Prepare your U.S. federal (1040 / 1040-NR / 8843) and California or New York income tax return.",
};

const SOURCE = "https://github.com/bhuvaneshnandipati/taxprep";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-ink focus:text-white focus:px-3 focus:py-2 focus:rounded-md text-sm">Skip to content</a>
        <header className="sticky top-0 z-40 bg-paper/85 backdrop-blur border-b border-hair">
          <div className="mx-auto max-w-6xl px-5 h-16 flex items-center justify-between gap-4">
            <a href="/dashboard" className="flex items-center gap-2.5">
              <span aria-hidden="true" className="grid place-items-center w-9 h-9 rounded-xl bg-ink text-white shadow-sheet">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
                  <path d="M6 3h9l3 3v15H6z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
                  <path d="M9 10h6M9 14h6M9 18h3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  <circle cx="17.5" cy="17.5" r="3.5" fill="#FFE066" stroke="#0F1A2A" strokeWidth="1.2" />
                </svg>
              </span>
              <span className="font-display font-extrabold text-[19px] tracking-tight">TaxPrep</span>
              <span className="hidden sm:inline font-mono text-[11px] px-2 py-0.5 rounded-full border border-rule text-mute">TY 2025 · FED + CA/NY</span>
            </a>
            <nav aria-label="Main" className="flex items-center gap-1 text-sm">
              <a className="px-3 py-2 rounded-full hover:bg-surface" href="/dashboard">Returns</a>
              <a className="hidden sm:inline-block px-3 py-2 rounded-full hover:bg-surface" href={SOURCE}>Source ↗</a>
            </nav>
          </div>
        </header>
        <div id="main" className="flex-1">{children}</div>
        <footer className="border-t border-hair mt-16">
          <div className="mx-auto max-w-6xl px-5 py-6 flex flex-wrap justify-between gap-3 text-[13px] text-mute">
            <span><span className="font-display font-bold text-ink">TaxPrep</span> · Form 8843 · 1040 / 1040-NR · CA 540 · NY IT-201</span>
            <a className="hover:text-ink underline underline-offset-4" href={SOURCE}>github.com/bhuvaneshnandipati/taxprep</a>
          </div>
        </footer>
      </body>
    </html>
  );
}
