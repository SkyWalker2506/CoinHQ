import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#3b82f6',
          hover: '#2563eb',
          muted: '#1d4ed8',
        },
        surface: {
          DEFAULT: '#111827',  // gray-900
          elevated: '#1f2937', // gray-800
          overlay: '#030712',  // gray-950
        },
        border: {
          DEFAULT: '#1f2937',  // gray-800
          muted: '#374151',    // gray-700
        },
      },
    },
  },
  plugins: [],
};

export default config;
