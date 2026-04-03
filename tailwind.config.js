/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./public/**/*.{html,js}",
  ],
  theme: {
    extend: {
      container: {
        maxWidth: 'none',
      },
    },
  },
  plugins: [],
}
