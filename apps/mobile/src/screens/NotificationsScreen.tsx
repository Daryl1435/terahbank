import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  Switch,
  TouchableOpacity,
  StyleSheet,
  Alert,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';
import { TerahIcon } from '@/components/TerahIcon';
import type { TerahIconName } from '@/components/TerahIcon';
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
  useNotificationPreferences,
  useUpdateNotificationPreferences,
} from '@/hooks/useNotifications';
import type { NotificationItem, NotificationPreferences } from '@/services/notifications';

type NotificationsNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Notifications'>;

interface NotificationsScreenProps {
  navigation: NotificationsNavigationProp;
}

// ── Notification type → icon + colour mapping ────────────────────────────────

interface IconSpec { name: TerahIconName; color: string; bg: string }

const TYPE_ICON: Record<string, IconSpec> = {
  KYC_APPROVED:        { name: 'checkmark-circle',   color: colors.success, bg: `${colors.success}18` },
  KYC_REJECTED:        { name: 'close-circle',        color: colors.error,   bg: `${colors.error}18`   },
  TRANSACTION_SUCCESS: { name: 'cash-outline',        color: colors.teal,    bg: `${colors.teal}18`    },
  TRANSACTION_FAILED:  { name: 'warning-outline',     color: colors.warning, bg: `${colors.warning}18` },
  MATURITY_REMINDER:   { name: 'alarm-outline',       color: colors.warning, bg: `${colors.warning}18` },
};

function getIconSpec(type: string): IconSpec {
  if (type.startsWith('PROJECT_MILESTONE')) {
    return { name: 'trophy-outline', color: colors.teal, bg: `${colors.teal}18` };
  }
  return TYPE_ICON[type] ?? { name: 'notifications-outline', color: colors.midGrey, bg: colors.lightGrey };
}

function formatRelativeDate(iso: string): string {
  const diff  = Date.now() - new Date(iso).getTime();
  const mins  = Math.floor(diff / 60_000);
  const hours = Math.floor(diff / 3_600_000);
  const days  = Math.floor(diff / 86_400_000);
  if (mins  <  1) return i18n.t('common.just_now') ?? "À l'instant";
  if (mins  < 60) return `${mins} min`;
  if (hours < 24) return `${hours}h`;
  return `${days}j`;
}

function NotificationRow({
  item,
  onPress,
}: {
  item: NotificationItem;
  onPress: (id: string) => void;
}) {
  const spec = getIconSpec(item.type);
  return (
    <TouchableOpacity
      style={[styles.row, !item.read && styles.rowUnread]}
      onPress={() => onPress(item.notification_id)}
      accessibilityRole="button"
    >
      {/* Coloured icon badge per notification type */}
      <View style={[styles.rowIconWrap, { backgroundColor: spec.bg }]}>
        <TerahIcon name={spec.name} size={20} color={spec.color} />
      </View>
      <View style={styles.rowContent}>
        <Text style={[styles.rowTitle, !item.read && styles.rowTitleUnread]} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={styles.rowBody} numberOfLines={2}>
          {item.body}
        </Text>
        <Text style={styles.rowDate}>{formatRelativeDate(item.created_at)}</Text>
      </View>
      {!item.read && <View style={styles.unreadDot} />}
    </TouchableOpacity>
  );
}

type Tab = 'inbox' | 'preferences';

type PrefKey = keyof NotificationPreferences;

const PREF_ROWS: { key: PrefKey; label: string }[] = [
  { key: 'push_enabled',        label: 'notifications.push_enabled' },
  { key: 'email_enabled',       label: 'notifications.email_enabled' },
  { key: 'sms_enabled',         label: 'notifications.sms_enabled' },
  { key: 'in_app_enabled',      label: 'notifications.in_app_enabled' },
  { key: 'transaction_alerts',  label: 'notifications.transaction_alerts' },
  { key: 'security_alerts',     label: 'notifications.security_alerts' },
  { key: 'monthly_summary',     label: 'notifications.monthly_summary' },
  { key: 'milestone_alerts',    label: 'notifications.milestone_alerts' },
  { key: 'maturity_reminders',  label: 'notifications.maturity_reminders' },
];

export default function NotificationsScreen({ navigation }: NotificationsScreenProps) {
  const [activeTab, setActiveTab] = useState<Tab>('inbox');

  const { data, isLoading, isRefetching, refetch, isError } = useNotifications();
  const markRead    = useMarkRead();
  const markAllRead = useMarkAllRead();

  const { data: prefs } = useNotificationPreferences();
  const updatePrefs = useUpdateNotificationPreferences();

  const notifications = data?.notifications ?? [];
  const hasUnread     = notifications.some((n) => !n.read);

  function handleMarkRead(id: string) {
    markRead.mutate(id, {
      onError: () => Alert.alert(i18n.t('common.error'), i18n.t('notifications.mark_read_error')),
    });
  }

  function handleMarkAllRead() {
    markAllRead.mutate(undefined, {
      onError: () => Alert.alert(i18n.t('common.error'), i18n.t('notifications.mark_read_error')),
    });
  }

  function handleTogglePref(key: PrefKey, value: boolean) {
    updatePrefs.mutate({ [key]: value });
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>

      {/* ── App Bar ──────────────────────────────────────────────────────────── */}
      <View style={styles.appBar}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <TerahIcon name="chevron-back" size={22} color="#fff" />
        </TouchableOpacity>

        <Text style={styles.appBarTitle}>{i18n.t('notifications.title')}</Text>

        {activeTab === 'inbox' && hasUnread ? (
          <TouchableOpacity
            onPress={handleMarkAllRead}
            style={styles.markAllButton}
            disabled={markAllRead.isPending}
          >
            <Text style={styles.markAllText}>{i18n.t('notifications.mark_all_read')}</Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.markAllButton} />
        )}
      </View>

      {/* ── Tabs ─────────────────────────────────────────────────────────────── */}
      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'inbox' && styles.tabActive]}
          onPress={() => setActiveTab('inbox')}
        >
          <Text style={[styles.tabText, activeTab === 'inbox' && styles.tabTextActive]}>
            {i18n.t('notifications.title')}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'preferences' && styles.tabActive]}
          onPress={() => setActiveTab('preferences')}
        >
          <Text style={[styles.tabText, activeTab === 'preferences' && styles.tabTextActive]}>
            {i18n.t('notifications.preferences_title')}
          </Text>
        </TouchableOpacity>
      </View>

      {/* ── Inbox tab ────────────────────────────────────────────────────────── */}
      {activeTab === 'inbox' && (
        isLoading ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={colors.teal} />
          </View>
        ) : isError ? (
          <View style={styles.centered}>
            <Text style={styles.errorText}>{i18n.t('notifications.load_error')}</Text>
            <TouchableOpacity onPress={() => refetch()} style={styles.retryButton}>
              <Text style={styles.retryText}>{i18n.t('common.retry')}</Text>
            </TouchableOpacity>
          </View>
        ) : notifications.length === 0 ? (
          <View style={styles.centered}>
            <View style={styles.emptyIconWrap}>
              <TerahIcon name="notifications-outline" size={40} color={colors.midGrey} />
            </View>
            <Text style={styles.emptyTitle}>{i18n.t('notifications.empty_title')}</Text>
            <Text style={styles.emptySubtitle}>{i18n.t('notifications.empty_subtitle')}</Text>
          </View>
        ) : (
          <ScrollView
            contentContainerStyle={styles.list}
            refreshControl={
              <RefreshControl
                refreshing={isRefetching}
                onRefresh={refetch}
                colors={[colors.teal]}
                tintColor={colors.teal}
              />
            }
          >
            {notifications.map((item) => (
              <NotificationRow key={item.notification_id} item={item} onPress={handleMarkRead} />
            ))}
          </ScrollView>
        )
      )}

      {/* ── Preferences tab ──────────────────────────────────────────────────── */}
      {activeTab === 'preferences' && (
        <ScrollView contentContainerStyle={styles.prefList}>
          {PREF_ROWS.map(({ key, label }) => (
            <View key={key} style={styles.prefRow}>
              <Text style={styles.prefLabel}>{i18n.t(label)}</Text>
              <Switch
                value={prefs ? prefs[key] : false}
                onValueChange={(val) => handleTogglePref(key, val)}
                trackColor={{ false: colors.lightGrey, true: colors.teal }}
                thumbColor="#fff"
                disabled={updatePrefs.isPending || prefs == null}
              />
            </View>
          ))}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  appBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.navy,
    height: 56,
    paddingHorizontal: 8,
  },
  backButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  appBarTitle: {
    flex: 1,
    color: '#fff',
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    textAlign: 'center',
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
  },
  tabActive: {
    borderBottomWidth: 2,
    borderBottomColor: colors.teal,
  },
  tabText: {
    fontSize: 14,
    color: colors.midGrey,
    fontFamily: 'Poppins_400Regular',
  },
  tabTextActive: {
    color: colors.teal,
    fontFamily: 'Poppins_600SemiBold',
  },
  prefList: {
    padding: 16,
  },
  prefRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 8,
    minHeight: 52,
  },
  prefLabel: {
    flex: 1,
    fontSize: 14,
    color: colors.darkGrey,
    fontFamily: 'Poppins_400Regular',
  },
  markAllButton: {
    width: 80,
    height: 44,
    justifyContent: 'center',
    alignItems: 'flex-end',
    paddingRight: 8,
  },
  markAllText: {
    color: colors.teal,
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
    textAlign: 'right',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
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
  emptyTitle: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    color: colors.darkGrey,
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: colors.midGrey,
    textAlign: 'center',
  },
  errorText: {
    fontSize: 14,
    color: colors.error,
    marginBottom: 12,
    textAlign: 'center',
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 10,
    backgroundColor: colors.teal,
    borderRadius: 8,
    minHeight: 44,
    justifyContent: 'center',
  },
  retryText: {
    color: '#fff',
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
  },
  list: {
    paddingVertical: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginVertical: 4,
    borderRadius: 12,
    padding: 12,
    minHeight: 72,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
    elevation: 1,
  },
  rowUnread: {
    backgroundColor: '#EBF8FF',
  },
  rowIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    flexShrink: 0,
  },
  rowContent: {
    flex: 1,
  },
  rowTitle: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    color: colors.darkGrey,
    marginBottom: 2,
  },
  rowTitleUnread: {
    fontFamily: 'Poppins_600SemiBold',
    color: colors.navy,
  },
  rowBody: {
    fontSize: 13,
    color: colors.midGrey,
    marginBottom: 4,
    lineHeight: 18,
  },
  rowDate: {
    fontSize: 11,
    color: colors.midGrey,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.teal,
    marginTop: 6,
    marginLeft: 8,
    flexShrink: 0,
  },
});
