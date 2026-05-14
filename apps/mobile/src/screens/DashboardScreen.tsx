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
  const touchActivity = useAppStore((s) => s.touchActivity);
  const isSessionExpired = useAppStore((s) => s.isSessionExpired);

  const { totalBalance, accounts, isLoading, refetch, isRefetching } = useTotalBalance();

  // FR-008: touch activity on every render
  useEffect(() => {
    touchActivity();
  });

  // FR-008: session expiry check
  useEffect(() => {
    if (isSessionExpired()) {
      navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
    }
  });

  const fullName = useAuthStore((s) => s.fullName);
  const firstName = fullName?.split(' ')[0] ?? '';
  const greetingKey = getGreetingKey();
  const greeting = i18n.t(greetingKey, { name: firstName });
  const { data: unreadCount } = useUnreadCount();

  return (
    <SafeAreaView style={styles.safe}>
      {/* ── App header (FR-049, FR-050) ─────────────────────────────────────── */}
      <View style={styles.appBar}>
        <TerahLogo variant="full" width={140} onDark />
        <View style={styles.appBarActions}>
          {/* FR-049: Notification bell with live unread badge */}
          <TouchableOpacity
            onPress={() => navigation.navigate('Notifications')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('dashboard.notifications')}
            style={styles.iconButton}
          >
            <Text style={styles.iconText}>🔔</Text>
            {unreadCount != null && unreadCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{unreadCount > 99 ? '99+' : String(unreadCount)}</Text>
              </View>
            )}
          </TouchableOpacity>

          {/* FR-050: Profile access */}
          <TouchableOpacity
            onPress={() => navigation.navigate('Profile')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('dashboard.profile')}
            style={styles.iconButton}
          >
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarInitial}>U</Text>
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

        {/* FR-046: Total balance card */}
        <View style={styles.balanceCard}>
          <Text style={styles.balanceLabel}>{i18n.t('dashboard.total_balance')}</Text>
          <Text style={styles.balanceAmount}>
            {isLoading ? '—' : formatXAF(totalBalance ?? 0)}
          </Text>
        </View>

        {/* FR-048: Quick action buttons */}
        <View style={styles.quickActions}>
          <TerahButton
            label={i18n.t('dashboard.deposit')}
            onPress={() => navigation.navigate('Deposit')}
            style={styles.actionButton}
          />
          <TerahButton
            label={i18n.t('dashboard.withdraw')}
            onPress={() => navigation.navigate('Withdraw')}
            variant="secondary"
            style={styles.actionButton}
          />
          <TerahButton
            label={i18n.t('dashboard.transfer')}
            onPress={() => navigation.navigate('Transfer')}
            variant="secondary"
            style={styles.actionButton}
          />
        </View>

        {/* Card shortcut */}
        <TouchableOpacity
          onPress={() => navigation.navigate('Cards')}
          style={styles.cardShortcut}
          accessibilityRole="button"
          activeOpacity={0.75}
        >
          <Text style={styles.cardShortcutIcon}>💳</Text>
          <Text style={styles.cardShortcutLabel}>{i18n.t('dashboard.my_cards')}</Text>
          <Text style={styles.cardShortcutChevron}>›</Text>
        </TouchableOpacity>

        {/* Insurance shortcut */}
        <TouchableOpacity
          onPress={() => navigation.navigate('Insurance')}
          style={styles.cardShortcut}
          accessibilityRole="button"
          activeOpacity={0.75}
        >
          <Text style={styles.cardShortcutIcon}>🛡</Text>
          <Text style={styles.cardShortcutLabel}>{i18n.t('dashboard.insurance')}</Text>
          <Text style={styles.cardShortcutChevron}>›</Text>
        </TouchableOpacity>

        {/* FR-047: Account list with tap-to-expand */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{i18n.t('dashboard.accounts_section')}</Text>
          <TouchableOpacity
            onPress={() => navigation.navigate('OpenAccount')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('dashboard.open_account')}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
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

        {/* Empty state */}
        {accounts?.length === 0 && !isLoading ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>🏦</Text>
            <Text style={styles.emptyText}>{i18n.t('accounts.no_accounts')}</Text>
            <Text style={styles.emptySubtext}>{i18n.t('accounts.open_first_account')}</Text>
            <TerahButton
              label={i18n.t('dashboard.open_account')}
              onPress={() => navigation.navigate('OpenAccount')}
              style={{ marginTop: 16 }}
            />
          </View>
        ) : null}

        {/* Bottom padding */}
        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.navy,
  },
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
    gap: 8,
  },
  iconButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    fontSize: 22,
  },
  badge: {
    position: 'absolute',
    top: 4,
    right: 4,
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
  balanceCard: {
    backgroundColor: colors.navy,
    marginHorizontal: 16,
    borderRadius: 16,
    padding: 24,
    marginBottom: 20,
  },
  balanceLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  balanceAmount: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 32,
    color: '#FFFFFF',
  },
  quickActions: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    marginBottom: 24,
  },
  actionButton: {
    flex: 1,
    height: 44,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  sectionTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 16,
    color: colors.navy,
  },
  addAccountLink: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.teal,
  },
  emptyState: {
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingTop: 32,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
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
  cardShortcut: {
    flexDirection:   'row',
    alignItems:      'center',
    backgroundColor: colors.white,
    marginHorizontal: 16,
    marginBottom:    20,
    borderRadius:    12,
    paddingHorizontal: 16,
    paddingVertical:  14,
  },
  cardShortcutIcon:    { fontSize: 22, marginRight: 12 },
  cardShortcutLabel:   { flex: 1, fontFamily: 'Poppins_600SemiBold', fontSize: 15, color: colors.navy },
  cardShortcutChevron: { fontSize: 22, color: colors.midGrey },
});
