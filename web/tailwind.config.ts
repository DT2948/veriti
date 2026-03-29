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
        ink: "#1E1724",
        panel: "#2C2230",
        panelSoft: "#3A2E39",
        elevated: "#453748",
        line: "#4E3E50",
        lineSubtle: "#3A2E39",
        primary: "#2F8C96",
        primaryHover: "#39A8B5",
        primarySubtle: "#1F5D64",
        official: "#22C55E",
        corroborated: "#F97316",
        plausible: "#EAB308",
        unverified: "#A89BA8",
        success: "#22C55E",
        danger: "#EF4444",
        textPrimary: "#EDE8ED",
        textSecondary: "#B7AEB7",
        textMuted: "#958A95",
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
