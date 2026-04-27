// Design System color tokens — always use these, never hardcode hex values
export const colors = {
  navy:      '#0B1F4A',   // Primary backgrounds, app bar
  teal:      '#00B4D8',   // CTAs, active states, accents
  tealDark:  '#0096B4',   // CTA press state
  offWhite:  '#F4F7FB',   // ALL screen backgrounds — never pure white
  lightGrey: '#E8EDF5',   // Borders, dividers
  midGrey:   '#8A97B5',   // Placeholder text, captions
  darkGrey:  '#4A5568',   // Body text
  darkNavy:  '#162D5E',   // Hover, gradient end
  white:     '#FFFFFF',   // Card backgrounds, text on dark
  success:   '#00C48C',   // Confirmed transactions, goal met
  warning:   '#FFB020',   // Pending, low balance
  error:     '#E53E3E',   // Failed, invalid input
  info:      '#00B4D8',   // Informational banners
} as const;

export const spacing = {
  xs:  4,
  sm:  8,
  md:  16,
  lg:  24,
  xl:  32,
  xxl: 48,
} as const;

export const radius = {
  sm:   4,
  md:   8,
  lg:   12,
  xl:   16,
  full: 9999,
} as const;

export const fontSize = {
  xs:   12,
  sm:   14,
  md:   16,
  lg:   18,
  xl:   22,
  xxl:  28,
} as const;
