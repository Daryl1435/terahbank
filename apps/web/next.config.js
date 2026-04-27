/** @type {import('next').NextConfig} */
const nextConfig = {
  // Transpile local workspace packages (TypeScript source)
  transpilePackages: ['@terahbank/tokens'],

  // Strict mode for catching React issues early
  reactStrictMode: true,

  // Disable X-Powered-By header in production
  poweredByHeader: false,

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options',        value: 'DENY' },
          { key: 'X-Content-Type-Options',  value: 'nosniff' },
          { key: 'Referrer-Policy',         value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy',      value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
