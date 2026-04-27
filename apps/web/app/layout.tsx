import type { Metadata } from 'next';
import { Poppins, Roboto } from 'next/font/google';
import './globals.css';

// ─── Fonts ────────────────────────────────────────────────────────────────────
// Poppins: headings, buttons, labels, nav items
const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-poppins',
  display: 'swap',
  preload: true,
});

// Roboto: body text, forms, captions, data tables
const roboto = Roboto({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-roboto',
  display: 'swap',
  preload: true,
});

// ─── Metadata ─────────────────────────────────────────────────────────────────
export const metadata: Metadata = {
  title: {
    template: '%s | TerahBank',
    default:  'TerahBank — Save. Grow. Thrive.',
  },
  description: 'Pan-African digital savings platform. Save, grow your money, and thrive. Cameroon-first.',
  icons: {
    icon: '/logo-symbol.svg',
    apple: '/logo-symbol.svg',
  },
  themeColor: '#0B1F4A',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
};

// ─── Root layout ──────────────────────────────────────────────────────────────
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="fr"
      className={`${poppins.variable} ${roboto.variable}`}
    >
      <body className="font-roboto bg-off-white text-dark-grey antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
