/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pp: {
          bg: '#090314', // deep night violet
          surface: '#120724', // dark purple surface
          card: '#180a33', // card background
          border: '#2e1254', // deep purple border
          borderPink: '#ec4899', // hot pink
          purple: '#9333ea', // royal purple
          purpleLight: '#c084fc', // light lavender purple
          pink: '#ec4899', // vibrant pink
          pinkLight: '#f472b6',
          white: '#ffffff',
          lavender: '#f3e8ff'
        }
      }
    },
  },
  plugins: [],
}
