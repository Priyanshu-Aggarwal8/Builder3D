/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#08090B',
        surface: '#0F1014',
        surfaceCard: '#14151B',
        surfaceHighlight: '#1A1C24',
        accentNeon: '#D4FF32',
        accentLime: '#C6F432',
        accentPurple: '#8B5CF6',
        accentCyan: '#38BDF8',
        accentDanger: '#FF4E4E',
        textPrimary: '#FFFFFF',
        textSecondary: '#8E8F9C',
        textMuted: '#585966',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2.5s infinite ease-in-out',
        'float': 'float 4s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 15px rgba(212, 255, 50, 0.2)' },
          '50%': { boxShadow: '0 0 35px rgba(212, 255, 50, 0.45)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        }
      }
    },
  },
  plugins: [],
}
