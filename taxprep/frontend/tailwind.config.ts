import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF7", ink: "#1A2332", formblue: "#2B5C8A",
        bluesoft: "#E8F0F7", rule: "#D8D6CE",
        refund: "#1E7A4D", owe: "#B3382C",
      },
      fontFamily: {
        sans: ["'Libre Franklin'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
