export type Carrier = 'mtn' | 'orange' | 'unknown';

/** Strip country code/spaces and return the 9-digit local number. */
function localDigits(phone: string): string {
  const cleaned = phone.replace(/[\s\-\+\(\)]/g, '');
  return cleaned.startsWith('237') ? cleaned.slice(3) : cleaned;
}

/**
 * Detect MTN or Orange Cameroon from a mobile number.
 * MTN: 65x, 67x, 68x — Orange: 69x
 */
export function detectCarrier(phone: string): Carrier {
  const local = localDigits(phone);
  if (local.length < 9 || !local.startsWith('6')) return 'unknown';
  const prefix = parseInt(local.substring(0, 2), 10);
  if (prefix === 65 || prefix === 67 || prefix === 68) return 'mtn';
  if (prefix === 69) return 'orange';
  return 'unknown';
}

/** Returns true if the string looks like a valid Cameroon mobile number. */
export function isValidCameroonPhone(phone: string): boolean {
  const local = localDigits(phone);
  return /^6[5-9]\d{7}$/.test(local);
}
