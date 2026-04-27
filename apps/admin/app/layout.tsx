import type { Metadata } from 'next';
import { Poppins, Roboto } from 'next/font/google';
import './globals.css';

const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-poppins',
  display: 'swap',
});

const roboto = Roboto({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-roboto',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    template: '%s | TerahBank Admin',
    default:  'TerahBank — Back Office',
  },
  description: 'TerahBank Operations Back-Office. Authorised personnel only.',
  robots: 'noindex, nofollow',   // Admin is never indexed
  icons: {
    icon: '/logo-symbol.svg',
  },
  themeColor: '#0B1F4A',
};

import Providers from './providers';

export default function AdminRootLayout({
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
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
