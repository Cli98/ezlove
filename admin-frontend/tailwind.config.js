/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#C44D3E',
        secondary: '#6B8F71',
        accent: '#D4A24E',
        surface: '#FBF7F2',
        'on-surface': '#2C2825',
        'on-surface-variant': '#9A8E82',
        'surface-container': '#F5EFE7',
        'outline-variant': '#E5DED5',
        'inactive-gray': '#C4BAB0',
        warning: '#E67E22',
        charcoal: '#2C2825',
        terracotta: '#A04828',
        outline: '#85736E',
        'primary-container': '#F4E8E4',
        'on-primary-container': '#410002',
        'surface-variant': '#E7E0D8',
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
        full: '9999px',
      },
      fontFamily: {
        headline: ['"Noto Serif SC"', 'serif'],
        display: ['"Noto Serif SC"', 'serif'],
        body: ['"Public Sans"', 'sans-serif'],
        label: ['"Public Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
