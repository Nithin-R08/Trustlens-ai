import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
    "./lib/**/*.{js,jsx,ts,tsx}",
    "./styles/**/*.css"
  ],
  theme: {
    extend: {
      colors: {
        void: "#131313",
        "void-soft": "#1c1b1b",
        neon: "#a4e6ff",
        "neon-strong": "#00d1ff",
        "slate-light": "#bbc9cf",
        violet: "#dcb8ff",
        alert: "#ffb4ab"
      },
      fontFamily: {
        headline: ["var(--font-headline)", "Space Grotesk", "sans-serif"],
        body: ["var(--font-body)", "Inter", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
