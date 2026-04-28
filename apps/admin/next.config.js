/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production';

// CSP for production only — dev mode needs unsafe-eval (webpack) and open connect-src (API + HMR)
const productionCSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "connect-src 'self' https://api.terahbank.com",
  "img-src 'self' data:",
].join('; ');

const nextConfig = {
  transpilePackages: ['@terahbank/tokens'],
  reactStrictMode: true,
  poweredByHeader: false,

  async headers() {
    const securityHeaders = [
      { key: 'X-Frame-Options',        value: 'DENY' },
      { key: 'X-Content-Type-Options',  value: 'nosniff' },
      { key: 'Referrer-Policy',         value: 'strict-origin-when-cross-origin' },
    ];

    // Only apply strict CSP in production — dev needs eval + open connect-src
    if (!isDev) {
      securityHeaders.push({ key: 'Content-Security-Policy', value: productionCSP });
    }

    return [{ source: '/(.*)', headers: securityHeaders }];
  },
};

module.exports = nextConfig;
