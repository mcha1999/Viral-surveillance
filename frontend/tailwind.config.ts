import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Risk level colors
        risk: {
          low: '#22c55e',      // Green
          medium: '#f59e0b',   // Amber
          high: '#ef4444',     // Red
          critical: '#7c2d12', // Dark red
        },
        // Wastewater "sludge" colors
        sludge: {
          receding: '#1e40af',  // Deep blue
          stable: '#6b7280',    // Neutral gray
          surging: '#dc2626',   // Glowing red
        },
        // Dark theme
        dark: {
          bg: '#0a0a0a',
          surface: '#171717',
          border: '#262626',
          muted: '#737373',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
  darkMode: 'class',
};

export default config;
