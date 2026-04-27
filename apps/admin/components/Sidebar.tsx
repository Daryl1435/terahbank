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
  roles?: AdminRole[];  // undefined = all roles
}

const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard',    label: 'Tableau de bord', icon: '⊞' },
  { href: '/users',        label: 'Utilisateurs',    icon: '👥' },
  { href: '/kyc',          label: 'File KYC',        icon: '📋' },
  { href: '/transactions', label: 'Transactions',    icon: '↔' },
  { href: '/fraud-alerts', label: 'Alertes fraude',  icon: '⚠' },
  { href: '/reports',      label: 'Rapports',        icon: '📊' },
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
          <span className="font-poppins font-bold text-base tracking-wide">
            TerahBank
            <span className="block text-teal text-xs font-roboto font-normal">Admin</span>
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded hover:bg-white/10 transition-colors text-mid-grey hover:text-white"
          aria-label={collapsed ? 'Développer le menu' : 'Réduire le menu'}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      {/* Role badge */}
      {!collapsed && role && (
        <div className="px-4 py-2 border-b border-white/10">
          <span className="text-xs text-mid-grey font-roboto">
            {role === 'super_admin'      && '👑 Super Admin'}
            {role === 'operations_staff' && '🛠 Opérations'}
            {role === 'read_only_analyst'&& '👁 Analyste'}
          </span>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto" aria-label="Navigation principale">
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
          title={collapsed ? 'Déconnexion' : undefined}
        >
          <span className="text-lg leading-none">⏏</span>
          {!collapsed && <span>Déconnexion</span>}
        </button>
      </div>
    </aside>
  );
}
