'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import clsx from 'clsx';
import { clearAuth, getRole, isSuperAdmin } from '@/lib/auth';
import type { AdminRole } from '@/lib/types';

interface NavItem {
  href:   string;
  label:  string;
  icon:   string;
  roles?: AdminRole[];
}

const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard',    label: 'Dashboard',      icon: '⊞' },
  { href: '/users',        label: 'Users',           icon: '👥' },
  { href: '/kyc',          label: 'KYC Queue',       icon: '📋' },
  { href: '/transactions', label: 'Transactions',    icon: '↔' },
  { href: '/fraud-alerts', label: 'Fraud Alerts',    icon: '⚠' },
  { href: '/reports',      label: 'Reports',         icon: '📊' },
  {
    href:  '/config',
    label: 'Configuration',
    icon:  '⚙',
    roles: ['super_admin'],
  },
];

export default function Sidebar() {
  const pathname  = usePathname();
  const router    = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const role = getRole();

  function handleLogout() {
    clearAuth();
    router.push('/login');
  }

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || (role && item.roles.includes(role)),
  );

  return (
    <aside
      className={clsx(
        'flex flex-col bg-navy text-white h-screen sticky top-0 transition-all duration-200',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/10 min-h-[64px]">
        {!collapsed && (
          <div className="flex items-center gap-2 min-w-0">
            <img src="/logo-symbol.svg" alt="TerahBank" className="h-7 flex-shrink-0" />
            <div className="min-w-0">
              <span className="font-poppins font-bold text-sm tracking-wide block">TerahBank</span>
              <span className="block text-teal text-xs font-roboto font-normal">Admin</span>
            </div>
          </div>
        )}
        {collapsed && (
          <img src="/logo-symbol.svg" alt="TerahBank" className="h-7 mx-auto" />
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded hover:bg-white/10 transition-colors text-mid-grey hover:text-white flex-shrink-0"
          aria-label={collapsed ? 'Expand menu' : 'Collapse menu'}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      {/* Role badge */}
      {!collapsed && role && (
        <div className="px-4 py-2 border-b border-white/10">
          <span className="text-xs text-mid-grey font-roboto">
            {role === 'super_admin'       && '👑 Super Admin'}
            {role === 'operations_staff'  && '🛠 Operations'}
            {role === 'read_only_analyst' && '👁 Analyst'}
          </span>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto" aria-label="Main navigation">
        {visibleItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-4 py-3 text-sm transition-colors',
                isActive
                  ? 'admin-nav-active text-white'
                  : 'text-mid-grey hover:text-white hover:bg-white/5',
                collapsed && 'justify-center px-0',
              )}
              title={collapsed ? item.label : undefined}
            >
              <span className="text-lg leading-none flex-shrink-0">{item.icon}</span>
              {!collapsed && <span className="font-roboto">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="border-t border-white/10 p-3">
        <button
          onClick={handleLogout}
          className={clsx(
            'flex items-center gap-3 w-full rounded px-3 py-2 text-sm text-mid-grey hover:text-white hover:bg-white/10 transition-colors',
            collapsed && 'justify-center',
          )}
          title={collapsed ? 'Sign out' : undefined}
        >
          <span className="text-lg leading-none">⏏</span>
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  );
}
