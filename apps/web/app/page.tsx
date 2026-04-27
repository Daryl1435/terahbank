import { redirect } from 'next/navigation';

/**
 * Root route — redirect to login.
 * The auth middleware (Phase 1) will redirect authenticated users to /dashboard.
 */
export default function RootPage() {
  redirect('/login');
}
