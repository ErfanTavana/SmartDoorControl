/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        accent: '#22d3ee',
        'accent-strong': '#0ea5e9',
      },
      boxShadow: {
        glow: '0 20px 50px rgba(0,0,0,0.35)',
      },
    },
  },
  plugins: [],
};
