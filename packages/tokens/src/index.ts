/**
 * @terahbank/tokens — TerahBank Design System v1.0
 *
 * Canonical source of truth for all visual constants.
 * Used by: apps/web, apps/admin
 * Mirrored in: apps/mobile/src/utils/tokens.ts
 *
 * Rules:
 * - Never hardcode hex values in components — always import from here
 * - All money amounts use BIGINT (see apps/api) — no floats here either
 */

// ─── Colors ───────────────────────────────────────────────────────────────────

export const colors = {
  navy:       '#0B1F4A',  // Primary backgrounds, app bar, sidebar
  teal:       '#00B4D8',  // CTAs, active states, accents, links
  tealDark:   '#0096B4',  // CTA hover/press state
  offWhite:   '#F4F7FB',  // ALL page backgrounds — never pure white
  lightGrey:  '#E8EDF5',  // Borders, dividers, table rows
  midGrey:    '#8A97B5',  // Placeholder text, captions, disabled
  darkGrey:   '#4A5568',  // Body text, labels
  darkNavy:   '#162D5E',  // Gradient end, hover on navy
  white:      '#FFFFFF',  // Card backgrounds, text on dark surfaces
  success:    '#00C48C',  // Confirmed transactions, KYC approved, goal met
  warning:    '#FFB020',  // Pending status, low balance, approaching limit
  error:      '#E53E3E',  // Failed transactions, validation errors, rejected KYC
  info:       '#00B4D8',  // Informational banners (same as teal)
} as const;

export type ColorToken = keyof typeof colors;

// ─── Spacing ──────────────────────────────────────────────────────────────────
// Base unit: 4px. All spacing is a multiple of 4.

export const spacing = {
  xs:   4,
  sm:   8,
  md:   16,
  lg:   24,
  xl:   32,
  xxl:  48,
  xxxl: 64,
} as const;

// ─── Border radius ────────────────────────────────────────────────────────────

export const radius = {
  sm:   4,
  md:   8,
  lg:   12,  // Default card radius
  xl:   16,
  full: 9999, // Pills, circular badges
} as const;

// ─── Font sizes ───────────────────────────────────────────────────────────────

export const fontSize = {
  xs:  12,
  sm:  14,
  md:  16,
  lg:  18,
  xl:  22,
  xxl: 28,
  xxxl:36,
} as const;

// ─── Typography families ──────────────────────────────────────────────────────

export const fontFamily = {
  heading: 'Poppins',   // Headings, buttons, labels, app bar titles
  body:    'Roboto',    // Body text, forms, captions, data tables
} as const;

// ─── Font weights ─────────────────────────────────────────────────────────────

export const fontWeight = {
  regular:   '400',
  medium:    '500',
  semiBold:  '600',
  bold:      '700',
} as const;

// ─── Shadows (CSS-ready) ──────────────────────────────────────────────────────

export const shadow = {
  card: '0 2px 8px rgba(11, 31, 74, 0.08)',       // Default card shadow
  modal:'0 8px 32px rgba(11, 31, 74, 0.16)',       // Modal / bottom sheet
  nav:  '0 2px 4px rgba(11, 31, 74, 0.06)',        // Top nav bar
} as const;

// ─── Breakpoints (CSS px values) ──────────────────────────────────────────────

export const breakpoint = {
  sm:  640,
  md:  768,
  lg:  1024,
  xl:  1280,
} as const;

// ─── Component dimension constants ────────────────────────────────────────────

export const size = {
  appBar:      56,   // Mobile app bar height (px)
  topNav:      72,   // Web/admin top nav height (px)
  adminSidebar:240,  // Admin sidebar expanded width (px)
  adminSidebarCollapsed: 64, // Admin sidebar icon-only width (px)
  bottomTab:   56,   // Mobile bottom tab bar height (px)
  inputHeight: 56,   // All text inputs (mobile + web)
  buttonHeight:56,   // All primary/secondary buttons
  minTouchTarget: 44, // WCAG — minimum touch/click target size
  maxContentWidth: 1280, // Web/admin max content width (px)
} as const;

// ─── CSS variable map (for web/admin globals.css) ─────────────────────────────
// Use cssVariables.colors to generate :root { ... } declarations.

export const cssVariables = {
  colors: {
    '--color-navy':       colors.navy,
    '--color-teal':       colors.teal,
    '--color-teal-dark':  colors.tealDark,
    '--color-off-white':  colors.offWhite,
    '--color-light-grey': colors.lightGrey,
    '--color-mid-grey':   colors.midGrey,
    '--color-dark-grey':  colors.darkGrey,
    '--color-dark-navy':  colors.darkNavy,
    '--color-white':      colors.white,
    '--color-success':    colors.success,
    '--color-warning':    colors.warning,
    '--color-error':      colors.error,
  },
} as const;
