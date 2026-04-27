// Tokens sourced from @terahbank/tokens — inlined here to avoid build-time transpilation.
// Keep in sync with packages/tokens/src/index.ts.

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        navy:         '#0B1F4A',
        teal:         '#00B4D8',
        'teal-dark':  '#0096B4',
        'off-white':  '#F4F7FB',
        'light-grey': '#E8EDF5',
        'mid-grey':   '#8A97B5',
        'dark-grey':  '#4A5568',
        'dark-navy':  '#162D5E',
        success:      '#00C48C',
        warning:      '#FFB020',
        error:        '#E53E3E',
      },
      fontFamily: {
        poppins: ['var(--font-poppins)', 'sans-serif'],
        roboto:  ['var(--font-roboto)',  'sans-serif'],
        sans:    ['var(--font-roboto)',  'sans-serif'],
      },
      width: {
        sidebar:           '240px',
        'sidebar-collapsed': '64px',
      },
      boxShadow: {
        card:  '0 2px 8px rgba(11, 31, 74, 0.08)',
        modal: '0 8px 32px rgba(11, 31, 74, 0.16)',
      },
    },
  },
  plugins: [],
};
