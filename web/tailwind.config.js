/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0F0F0F",
        surface: "#1A1A1A",
        surfaceLight: "#242424",
        border: "#2A2A2A",
        borderLight: "#333333",
        accent: "#5BBFBA",
        accentDark: "#4A9E9A",
        textPrimary: "#F5F5F5",
        textSecondary: "#999999",
        textMuted: "#666666",
        danger: "#E74C3C",
        warn: "#F59E0B",
        ok: "#4CAF50",
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
