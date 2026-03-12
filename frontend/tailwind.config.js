/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nexus: {
          bg: 'var(--nexus-bg)',
          card: 'var(--nexus-card)',
          cardHover: 'var(--nexus-card-hover)',
          border: 'var(--nexus-border)',
          text: 'var(--nexus-text)',
          textMuted: 'var(--nexus-text-muted)',
          primary: '#B19EEF',
          secondary: '#826EEA'
        }
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 8px 32px 0 var(--nexus-shadow)',
      },
      backdropBlur: {
        glass: '16px',
      }
    },
  },
  plugins: [],
}
