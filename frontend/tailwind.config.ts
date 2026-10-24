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
        background: "#07090E",
        surface: {
          DEFAULT: "#0E131F",
          elevated: "#141C2B",
          hover: "#1A2538",
          glass: "rgba(14, 19, 31, 0.75)",
        },
        border: {
          subtle: "#1B2436",
          strong: "#2B3A55",
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
          ice: "#65E4F3",
          dim: "rgba(101, 228, 243, 0.12)",
          glow: "rgba(101, 228, 243, 0.25)",
        },
        amber: {
          attention: "#FFB454",
          dim: "rgba(255, 180, 84, 0.12)",
          glow: "rgba(255, 180, 84, 0.25)",
        },
        semantic: {
          success: "#3FB950",
          danger: "#F85149",
        },
        text: {
          primary: "#F1F5F9",
          secondary: "#94A3B8",
          muted: "#64748B",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Inter",
          "Noto Sans",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "Liberation Mono",
          "Courier New",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
