// Input validators — used in registration, login, and transaction forms

// FR-003: min 10 chars, 1 uppercase, 1 number, 1 special char
export const validatePassword = (password: string): string | null => {
  if (password.length < 10) return 'Password must be at least 10 characters.';
  if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter.';
  if (!/[0-9]/.test(password)) return 'Password must contain at least one number.';
  if (!/[^A-Za-z0-9]/.test(password)) return 'Password must contain at least one special character.';
  return null;
};

// E.164 format for Cameroon numbers (+237...)
export const validatePhoneNumber = (phone: string): string | null => {
  const e164Regex = /^\+[1-9]\d{1,14}$/;
  if (!e164Regex.test(phone)) return 'Enter a valid phone number in international format (e.g. +237...)';
  return null;
};

export const validateEmail = (email: string): string | null => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email.toLowerCase())) return 'Enter a valid email address.';
  return null;
};

// OTP: exactly 6 digits
export const validateOTP = (otp: string): boolean => /^\d{6}$/.test(otp);

// PIN: exactly 6 digits (numeric keypad — never exposed via system keyboard)
export const validatePIN = (pin: string): boolean => /^\d{6}$/.test(pin);

// Amount: positive integer in smallest XAF unit (BIGINT — never float)
export const validateAmount = (amount: number, minAmount = 0): string | null => {
  if (!Number.isInteger(amount)) return 'Amount must be a whole number.';
  if (amount <= 0) return 'Amount must be greater than zero.';
  if (amount < minAmount) return `Minimum amount is ${minAmount} XAF.`;
  return null;
};

export const validateFullName = (name: string): string | null => {
  if (name.trim().length < 2) return 'Full name must be at least 2 characters.';
  if (name.trim().length > 255) return 'Full name is too long.';
  return null;
};
