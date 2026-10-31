import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#08090D",
        surface: {
          DEFAULT: "#0E131F",
          elevated: "#151D2C",
          hover: "#1A2538",
          glass: "rgba(14, 19, 31, 0.75)",
        },
        border: {
          subtle: "rgba(255, 255, 255, 0.08)",
          strong: "rgba(255, 255, 255, 0.16)",
          glow: "rgba(0, 242, 254, 0.25)",
        },
        cyber: {
          cyan: "#00F2FE",
          mint: "#00F5A0",
          purple: "#8B5CF6",
          pink: "#F43F5E",
          emerald: "#10B981",
        },
        forge: {
          lime: "#D7FF64",
          "lime-dim": "rgba(215, 255, 100, 0.12)",
          "lime-glow": "rgba(215, 255, 100, 0.25)",
        },
        ultraviolet: {
          DEFAULT: "#A78BFA",
          dim: "rgba(167, 139, 250, 0.12)",
          glow: "rgba(167, 139, 250, 0.25)",
        },
        cyan: {
          ice: "#38BDF8",
          dim: "rgba(56, 189, 248, 0.12)",
          glow: "rgba(56, 189, 248, 0.25)",
        },
        amber: {
          attention: "#F59E0B",
          dim: "rgba(245, 158, 11, 0.12)",
          glow: "rgba(245, 158, 11, 0.25)",
        },
        semantic: {
          success: "#10B981",
          danger: "#EF4444",
        },
        text: {
          primary: "#F8FAFC",
          secondary: "#CBD5E1",
          muted: "#94A3B8",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-sans)",
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "var(--font-mono)",
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
