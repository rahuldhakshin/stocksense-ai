import forms from "@tailwindcss/forms";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0E1A",
        card: "#0F1629",
        accent: "#00D4AA",
        danger: "#FF6B35",
        buy: "#00C851",
        muted: "#8C96B8",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        terminal: "0 0 0 1px rgba(0, 212, 170, 0.08), 0 18px 50px rgba(0, 0, 0, 0.35)",
      },
      keyframes: {
        pulseSignal: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.95" },
          "50%": { transform: "scale(1.05)", opacity: "1" },
        },
      },
      animation: {
        "pulse-signal": "pulseSignal 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [forms],
};
