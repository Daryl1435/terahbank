'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import clsx from 'clsx';
import {
  LayoutDashboard,
  Users,
  ClipboardCheck,
  ArrowLeftRight,
  ShieldAlert,
  BarChart3,
  Settings,
  LogOut,
  Crown,
  Wrench,
  Eye,
  ChevronLeft,
  ChevronRight,
  Globe,
} from 'lucide-react';
import { clearAuth, getRole } from '@/lib/auth';
import { useTranslation } from '@/lib/i18n';
import type { AdminRole } from '@/lib/types';

interface NavItem {
  href:     string;
  labelKey: 'nav.dashboard' | 'nav.users' | 'nav.kyc' | 'nav.transactions' | 'nav.fraudAlerts' | 'nav.reports' | 'nav.config';
  icon:     React.ComponentType<{ className?: string }>;
  roles?:   AdminRole[];
}

const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard',    labelKey: 'nav.dashboard',    icon: LayoutDashboard },
  { href: '/users',        labelKey: 'nav.users',         icon: Users },
  { href: '/kyc',          labelKey: 'nav.kyc',           icon: ClipboardCheck },
  { href: '/transactions', labelKey: 'nav.transactions',  icon: ArrowLeftRight },
  { href: '/fraud-alerts', labelKey: 'nav.fraudAlerts',   icon: ShieldAlert },
  { href: '/reports',      labelKey: 'nav.reports',       icon: BarChart3 },
  { href: '/config',       labelKey: 'nav.config',        icon: Settings, roles: ['super_admin'] },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router   = useRouter();
  const { t, lang, setLang } = useTranslation();
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
          aria-label={collapsed ? t('sidebar.expandAriaLabel') : t('sidebar.collapseAriaLabel')}
        >
          {collapsed
            ? <ChevronRight className="w-4 h-4" />
            : <ChevronLeft  className="w-4 h-4" />
          }
        </button>
      </div>

      {/* Role badge */}
      {!collapsed && role && (
        <div className="px-4 py-2 border-b border-white/10 flex items-center gap-1.5">
          {role === 'super_admin'       && <Crown  className="w-3.5 h-3.5 text-mid-grey flex-shrink-0" />}
          {role === 'operations_staff'  && <Wrench className="w-3.5 h-3.5 text-mid-grey flex-shrink-0" />}
          {role === 'read_only_analyst' && <Eye    className="w-3.5 h-3.5 text-mid-grey flex-shrink-0" />}
          <span className="text-xs text-mid-grey font-roboto">
            {role === 'super_admin'       && t('role.superAdmin')}
            {role === 'operations_staff'  && t('role.operations')}
            {role === 'read_only_analyst' && t('role.analyst')}
          </span>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto" aria-label="Main navigation">
        {visibleItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          const Icon = item.icon;
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
              title={collapsed ? t(item.labelKey) : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span className="font-roboto">{t(item.labelKey)}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Language toggle + Logout */}
      <div className="border-t border-white/10 p-3 flex flex-col gap-1">
        <button
          onClick={() => setLang(lang === 'en' ? 'fr' : 'en')}
          className={clsx(
            'flex items-center gap-3 w-full rounded px-3 py-2 text-sm text-mid-grey hover:text-white hover:bg-white/10 transition-colors',
            collapsed && 'justify-center',
          )}
          title={collapsed ? t('lang.toggle') : undefined}
          aria-label={`Switch to ${lang === 'en' ? 'Français' : 'English'}`}
        >
          <Globe className="w-5 h-5 flex-shrink-0" />
          {!collapsed && (
            <span className="font-mono text-xs font-medium tracking-wider">
              {t('lang.toggle')}
            </span>
          )}
        </button>

        <button
          onClick={handleLogout}
          className={clsx(
            'flex items-center gap-3 w-full rounded px-3 py-2 text-sm text-mid-grey hover:text-white hover:bg-white/10 transition-colors',
            collapsed && 'justify-center',
          )}
          title={collapsed ? t('nav.signOut') : undefined}
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span>{t('nav.signOut')}</span>}
        </button>
      </div>
    </aside>
  );
}
