const { getDefaultConfig } = require('expo/metro-config');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

// uuid v10 uses import.meta in its ESM build, which Metro can't bundle for web.
// Disabling package exports forces Metro to use the CommonJS build instead.
config.resolver.unstable_enablePackageExports = false;

module.exports = config;
