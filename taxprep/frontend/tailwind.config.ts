import type { Config } from "tailwindcss";
/* TaxPrep "ledger" design system.
   Token names are kept from the original design so page markup stays stable:
   formblue = primary action blue, bluesoft = its tint, refund = green, owe = red-orange,
   marker = highlighter yellow used for focus and form-line emphasis. */
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F4EE", surface: "#FFFFFF", ink: "#0F1A2A", night: "#0B1422",
        formblue: "#1D3FD6", cobaltdeep: "#142FA8", bluesoft: "#E6EBFD",
        marker: "#FFE066", markersoft: "#FFF6CC",
        rule: "#DCD8CC", hair: "#ECE9E0", mute: "#5B6472",
        refund: "#0E8A5F", owe: "#C2410C",
        gray: { 400: "#8A919C", 500: "#5B6472", 600: "#475061", 700: "#323A48" },
      },
      fontFamily: {
        sans: ["'Geist'", "system-ui", "-apple-system", "'Segoe UI'", "sans-serif"],
        display: ["'Bricolage Grotesque'", "'Geist'", "system-ui", "sans-serif"],
        mono: ["'Geist Mono'", "ui-monospace", "Menlo", "monospace"],
      },
      boxShadow: {
        sheet: "0 1px 0 rgba(15,26,42,.04), 0 12px 32px -16px rgba(15,26,42,.18)",
        lift: "0 2px 0 rgba(15,26,42,.06), 0 24px 48px -20px rgba(15,26,42,.28)",
      },
      keyframes: {
        post: { "0%": { opacity: "0", transform: "translateY(6px)" }, "100%": { opacity: "1", transform: "none" } },
      },
      animation: { post: "post .5s cubic-bezier(.2,.7,.1,1) both" },
    },
  },
  plugins: [],
} satisfies Config;
