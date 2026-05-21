import React, { useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { useAuthStore } from '@/stores/authStore';
import { useAppStore } from '@/stores/appStore';
import { useTotalBalance } from '@/hooks/useBalance';
import { AccountCard } from '@/components/AccountCard';
import { TerahButton } from '@/components/TerahButton';
import { TerahLogo } from '@/components/TerahLogo';
import { TerahIcon } from '@/components/TerahIcon';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';
import { useUnreadCount } from '@/hooks/useNotifications';

type DashboardNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Dashboard'>;

interface DashboardScreenProps {
  navigation: DashboardNavigationProp;
}

const getGreetingKey = (): string => {
  const hour = new Date().getHours();
  if (hour < 12) return 'dashboard.greeting_morning';
  if (hour < 18) return 'dashboard.greeting_afternoon';
  return 'dashboard.greeting_evening';
};

export default function DashboardScreen({ navigation }: DashboardScreenProps) {
  const touchActivity  = useAppStore((s) => s.touchActivity);
  const isSessionExpired = useAppStore((s) => s.isSessionExpired);

  const { totalBalance, accounts, isLoading, refetch, isRefetching } = useTotalBalance();

  // FR-008: touch activity on every render
  useEffect(() => { touchActivity(); });

  // FR-008: session expiry check
  useEffect(() => {
    if (isSessionExpired()) {
      navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
    }
  });

  const fullName  = useAuthStore((s) => s.fullName);
  const firstName = fullName?.split(' ')[0] ?? '';
  const greeting  = i18n.t(getGreetingKey(), { name: firstName });

  const { data: unreadCount } = useUnreadCount();

  return (
    <SafeAreaView style={styles.safe}>

      {/* ── App bar ─────────────────────────────────────────────────────────── */}
      <View style={styles.appBar}>
        <TerahLogo variant="full" width={140} onDark />

        <View style={styles.appBarActions}>

          {/* Notification bell with live unread badge (FR-049) */}
          <TouchableOpacity
            onPress={() => navigation.navigate('Notifications')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('dashboard.notifications')}
            style={styles.iconButton}
          >
            <TerahIcon
              name={unreadCount ? 'notifications' : 'notifications-outline'}
              size={24}
              color={colors.white}
            />
            {unreadCount != null && unreadCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>
                  {unreadCount > 99 ? '99+' : String(unreadCount)}
                </Text>
              </View>
            )}
          </TouchableOpacity>

          {/* Avatar / profile shortcut (FR-050) */}
          <TouchableOpacity
            onPress={() => navigation.navigate('Profile')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('dashboard.profile')}
            style={styles.iconButton}
          >
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarInitial}>
                {firstName.charAt(0).toUpperCase() || 'U'}
              </Text>
            </View>
          </TouchableOpacity>

        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
      >

        {/* Greeting */}
        <Text style={styles.greeting}>{greeting}</Text>

        {/* ── Total balance card (FR-046) ──────────────────────────────────── */}
        <View style={styles.balanceCard}>
          {/* Teal accent strip across the top of the card */}
          <View style={styles.balanceCardAccent} />

          <View style={styles.balanceCardInner}>
            <Text style={styles.balanceLabel}>{i18n.t('dashboard.total_balance')}</Text>
            <Text style={styles.balanceAmount}>
              {isLoading ? '—' : formatXAF(totalBalance ?? 0)}
            </Text>

            {/* Quick link to full transaction history */}
            <TouchableOpacity
              onPress={() => navigation.navigate('TransactionHistory', {})}
              style={styles.historyLink}
              accessibilityRole="button"
            >
              <Text style={styles.historyLinkText}>{i18n.t('dashboard.view_history')}</Text>
              <TerahIcon name="arrow-forward" size={13} color={colors.teal} />
            </TouchableOpacity>
          </View>
        </View>

        {/* ── Quick action buttons (FR-048) ───────────────────────────────── */}
        <View style={styles.quickActionsCard}>
          <QuickAction
            icon="arrow-down-circle-outline"
            label={i18n.t('dashboard.deposit')}
            onPress={() => navigation.navigate('Deposit')}
            primary
          />
          <View style={styles.quickDivider} />
          <QuickAction
            icon="arrow-up-circle-outline"
            label={i18n.t('dashboard.withdraw')}
            onPress={() => navigation.navigate('Withdraw')}
          />
          <View style={styles.quickDivider} />
          <QuickAction
            icon="swap-horizontal-outline"
            label={i18n.t('dashboard.transfer')}
            onPress={() => navigation.navigate('Transfer')}
          />
        </View>

        {/* ── My Cards shortcut ────────────────────────────────────────────── */}
        <ShortcutRow
          icon="card-outline"
          label={i18n.t('dashboard.my_cards')}
          onPress={() => navigation.navigate('Cards')}
        />

        {/* ── Insurance shortcut ───────────────────────────────────────────── */}
        <ShortcutRow
          icon="shield-checkmark-outline"
          label={i18n.t('dashboard.insurance')}
          onPress={() => navigation.navigate('Insurance')}
        />

        {/* ── Accounts section (FR-047) ────────────────────────────────────── */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{i18n.t('dashboard.accounts_section')}</Text>
          <TouchableOpacity
            onPress={() => navigation.navigate('OpenAccount')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('dashboard.open_account')}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            style={styles.openAccountBtn}
          >
            <TerahIcon name="add-circle-outline" size={15} color={colors.teal} />
            <Text style={styles.addAccountLink}>{i18n.t('dashboard.open_account')}</Text>
          </TouchableOpacity>
        </View>

        {accounts?.map((account) => (
          <AccountCard
            key={account.account_id}
            account={account}
            onPress={() =>
              navigation.navigate('AccountDetail', { accountId: account.account_id })
            }
          />
        ))}

        {/* Empty state — shown when no accounts exist */}
        {accounts?.length === 0 && !isLoading && (
          <View style={styles.emptyState}>
            <View style={styles.emptyIconWrap}>
              <TerahIcon name="business-outline" size={42} color={colors.midGrey} />
            </View>
            <Text style={styles.emptyText}>{i18n.t('accounts.no_accounts')}</Text>
            <Text style={styles.emptySubtext}>{i18n.t('accounts.open_first_account')}</Text>
            <TerahButton
              label={i18n.t('dashboard.open_account')}
              onPress={() => navigation.navigate('OpenAccount')}
              style={{ marginTop: 16 }}
            />
          </View>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Quick action sub-component ────────────────────────────────────────────────

interface QuickActionProps {
  icon:    string;
  label:   string;
  onPress: () => void;
  primary?: boolean;
}

function QuickAction({ icon, label, onPress, primary }: QuickActionProps) {
  return (
    <TouchableOpacity
      style={styles.quickAction}
      onPress={onPress}
      activeOpacity={0.75}
      accessibilityRole="button"
    >
      <TerahIcon
        name={icon as any}
        size={26}
        color={primary ? colors.teal : colors.navy}
      />
      <Text style={[styles.quickActionLabel, primary && styles.quickActionLabelPrimary]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

// ── Shortcut row sub-component ────────────────────────────────────────────────

interface ShortcutRowProps {
  icon:    string;
  label:   string;
  onPress: () => void;
}

function ShortcutRow({ icon, label, onPress }: ShortcutRowProps) {
  return (
    <TouchableOpacity
      style={styles.shortcut}
      onPress={onPress}
      accessibilityRole="button"
      activeOpacity={0.75}
    >
      <View style={styles.shortcutIconWrap}>
        <TerahIcon name={icon as any} size={20} color={colors.teal} />
      </View>
      <Text style={styles.shortcutLabel}>{label}</Text>
      <TerahIcon name="chevron-forward" size={18} color={colors.midGrey} />
    </TouchableOpacity>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.navy,
  },

  // App bar
  appBar: {
    backgroundColor: colors.navy,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
    height: 64,
  },
  appBarActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  iconButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: 6,
    right: 6,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.error,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 2,
  },
  badgeText: {
    color: '#fff',
    fontSize: 9,
    fontFamily: 'Poppins_600SemiBold',
    lineHeight: 14,
  },
  avatarCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitial: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: '#FFFFFF',
  },

  // Scrollable content
  scroll: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    paddingBottom: 32,
  },
  greeting: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 18,
    color: colors.navy,
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 16,
  },

  // Balance card
  balanceCard: {
    backgroundColor: colors.navy,
    marginHorizontal: 16,
    borderRadius: 20,
    marginBottom: 20,
    overflow: 'hidden',
    // Subtle elevation
    shadowColor: colors.navy,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 6,
  },
  // Teal accent strip at the top of the balance card
  balanceCardAccent: {
    height: 4,
    backgroundColor: colors.teal,
    width: '40%',
    borderRadius: 2,
    marginTop: 0,
  },
  balanceCardInner: {
    padding: 24,
    paddingTop: 20,
  },
  balanceLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  balanceAmount: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 34,
    color: '#FFFFFF',
    letterSpacing: -0.5,
  },
  historyLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 12,
    alignSelf: 'flex-start',
  },
  historyLinkText: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 12,
    color: colors.teal,
  },

  // Quick actions card
  quickActionsCard: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    marginHorizontal: 16,
    borderRadius: 16,
    marginBottom: 20,
    paddingVertical: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  quickAction: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    gap: 6,
    minHeight: 72,
  },
  quickDivider: {
    width: 1,
    backgroundColor: colors.lightGrey,
    marginVertical: 12,
  },
  quickActionLabel: {
    fontFamily: 'Poppins_500Medium',
    fontSize: 12,
    color: colors.navy,
    textAlign: 'center',
  },
  quickActionLabelPrimary: {
    color: colors.teal,
  },

  // Shortcut rows (Cards, Insurance)
  shortcut: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
    minHeight: 56,
  },
  shortcutIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: `${colors.teal}18`,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  shortcutLabel: {
    flex: 1,
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: colors.navy,
  },

  // Section header
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    marginBottom: 12,
    marginTop: 4,
  },
  sectionTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 16,
    color: colors.navy,
  },
  openAccountBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  addAccountLink: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.teal,
  },

  // Empty state
  emptyState: {
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingTop: 32,
  },
  emptyIconWrap: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.lightGrey,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  emptyText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 16,
    color: colors.navy,
    textAlign: 'center',
    marginBottom: 8,
  },
  emptySubtext: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    textAlign: 'center',
  },
});
