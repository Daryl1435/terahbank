/**
 * Format a BIGINT amount (smallest XAF unit) for display.
 * Always use this — never format XAF inline.
 */
export const formatXAF = (amountInSmallestUnit: number, locale: string = 'fr'): string => {
  const amount = amountInSmallestUnit / 100;
  return new Intl.NumberFormat(locale === 'fr' ? 'fr-CM' : 'en-CM', {
    style: 'currency',
    currency: 'XAF',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};
// formatXAF(500000, 'fr') → "5 000 XAF"
// formatXAF(500000, 'en') → "XAF 5,000"
