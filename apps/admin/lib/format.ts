// Display formatting helpers.

/** Format BIGINT XAF amount (integer units) as human-readable currency string. */
export function formatXAF(amount: number): string {
  return new Intl.NumberFormat('fr-CM', {
    style: 'currency',
    currency: 'XAF',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Format ISO date string as locale date + time. */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('fr-CM', {
    day:    '2-digit',
    month:  '2-digit',
    year:   'numeric',
    hour:   '2-digit',
    minute: '2-digit',
  }).format(new Date(iso));
}

/** Format ISO date string as date only. */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('fr-CM', {
    day:   '2-digit',
    month: '2-digit',
    year:  'numeric',
  }).format(new Date(iso));
}

/** Mask phone number: +237 6XX XXX XXX → +237 6•• ••• ••3 */
export function maskPhone(phone: string): string {
  if (phone.length < 6) return phone;
  return phone.slice(0, 5) + '•'.repeat(phone.length - 8) + phone.slice(-3);
}
