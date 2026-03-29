import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0a0f1a",
        panel: "#111827",
        panelSoft: "#1a2332",
        line: "#1e293b",
        lineSubtle: "#162032",
        official: "#3B82F6",
        corroborated: "#F97316",
        plausible: "#EAB308",
        unverified: "#64748B",
        success: "#22C55E",
        danger: "#EF4444",
      },
      boxShadow: {
        panel: "none",
      },
      animation: {
        pulseMarker: "pulse 2s ease-in-out infinite",
        flashCard: "flash 2.2s ease-in-out",
      },
    },
  },
  plugins: [],
};

export default config;
