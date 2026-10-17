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
        background: "#0B0D0F",
        surface: {
          DEFAULT: "#14181C",
          elevated: "#1D242A",
          hover: "#222B32",
        },
        border: {
          subtle: "#242C34",
          strong: "#333D48",
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
          primary: "#F1F4ED",
          secondary: "#87919A",
          muted: "#5B656F",
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
