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
          bg: '#0A0A0A',
          card: 'rgba(255, 255, 255, 0.05)',
          cardHover: 'rgba(255, 255, 255, 0.08)',
          border: 'rgba(255, 255, 255, 0.1)',
          primary: '#B19EEF',
          secondary: '#826EEA'
        }
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
      },
      backdropBlur: {
        glass: '16px',
      }
    },
  },
  plugins: [],
}
