// Tokens are sourced from @terahbank/tokens — values inlined here to avoid
// runtime transpilation during Tailwind's JIT scan. Keep in sync with packages/tokens/src/index.ts.

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
        sans:    ['var(--font-roboto)',  'sans-serif'], // default sans
      },
      spacing: {
        '18': '72px',  // top nav height
      },
      maxWidth: {
        content: '1280px',
      },
      boxShadow: {
        card:  '0 2px 8px rgba(11, 31, 74, 0.08)',
        modal: '0 8px 32px rgba(11, 31, 74, 0.16)',
        nav:   '0 2px 4px rgba(11, 31, 74, 0.06)',
      },
      animation: {
        'gradient-orb':         'gradient-orb 8s ease-in-out infinite alternate',
        'gradient-orb-delayed': 'gradient-orb 8s ease-in-out 4s infinite alternate',
        float:                  'float 6s ease-in-out infinite',
        'fade-up':              'fade-up 0.6s ease-out forwards',
      },
      keyframes: {
        'gradient-orb': {
          '0%':   { transform: 'translate(0, 0) scale(1)' },
          '100%': { transform: 'translate(40px, -30px) scale(1.15)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-10px)' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'dot-grid':        "radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)",
      },
      backgroundSize: {
        'dot-grid': '28px 28px',
      },
    },
  },
  plugins: [],
};
