import { redirect } from 'next/navigation';

/**
 * Admin root — redirect to admin login.
 * Admin auth middleware (Milestone 5.2) will redirect authenticated
 * admins to /dashboard after verifying role + TOTP.
 */
export default function AdminRootPage() {
  redirect('/login');
}
