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
        ink: "#08101b",
        panel: "#0f1726",
        panelSoft: "#162033",
        line: "#243148",
        official: "#4c8dff",
        corroborated: "#ef4444",
        plausible: "#f59e0b",
        unverified: "#94a3b8",
      },
      boxShadow: {
        panel: "0 18px 40px rgba(0, 0, 0, 0.28)",
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
