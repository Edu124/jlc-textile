/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // iOS-style elevated dark palette (matches the desktop app)
        bg: "#1C1C1E",
        sidebar: "#161618",
        surface: "#2C2C2E",
        surface2: "#3A3A3C",
        surface3: "#48484A",
        separator: "#38383A",
        bordr: "#48484A",
        ink: "#F5F5F7",
        ink2: "#C7C7CC",
        ink3: "#AEAEB2",
        muted: "#8E8E93",
        accent: "#5E7E9B",
        accentHover: "#6E8FAC",
        accentSoft: "#2B3845",
        ok: "#5FB07C",
        okSoft: "#1E3325",
        danger: "#D9685F",
        dangerSoft: "#36211F",
        warn: "#D9A45B",
        warnSoft: "#332919",
        info: "#7FA8B8",
      },
      fontFamily: {
        sans: ['"Segoe UI"', "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: { xl2: "14px" },
    },
  },
  plugins: [],
};
