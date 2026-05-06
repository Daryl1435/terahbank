/**
 * FR-037: Transaction history — searchable, filterable, paginated.
 *
 * Filters: All | Pending | Successful | Failed (status tabs)
 * Optional: filtered to a specific account_id (from AccountDetailScreen).
 * Pull-to-refresh. Tap a row → TransactionDetailScreen.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { useTransactions } from '@/hooks/useTransactions';
import { TransactionItem } from '@/components/TransactionItem';
import { TerahButton } from '@/components/TerahButton';
import type { Transaction } from '@/services/transactions';
import { colors, spacing, radius } from '@/utils/tokens';
import i18n from '@/locales';

type HistoryNavProp = NativeStackNavigationProp<RootStackParamList, 'TransactionHistory'>;
type HistoryRouteProp = RouteProp<RootStackParamList, 'TransactionHistory'>;

interface TransactionHistoryScreenProps {
  navigation: HistoryNavProp;
  route: HistoryRouteProp;
}

type StatusFilter = 'all' | 'pending' | 'success' | 'failed';

const FILTERS: Array<{ id: StatusFilter; labelKey: string }> = [
  { id: 'all',     labelKey: 'transactions.history_all' },
  { id: 'pending', labelKey: 'transactions.history_pending' },
  { id: 'success', labelKey: 'transactions.history_success' },
  { id: 'failed',  labelKey: 'transactions.history_failed' },
];

export default function TransactionHistoryScreen({
  navigation,
  route,
}: TransactionHistoryScreenProps) {
  const accountId = route.params?.accountId;
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const { data, isLoading, isError, refetch, isRefetching } = useTransactions({
    account_id: accountId,
    status: statusFilter === 'all' ? undefined : statusFilter,
    limit: 50,
  });

  const transactions: Transaction[] = Array.isArray(data)
    ? data
    : (data as any)?.transactions ?? [];

  const renderItem = ({ item }: { item: Transaction }) => (
    <TouchableOpacity
      activeOpacity={0.75}
      onPress={() =>
        navigation.navigate('TransactionDetail', {
          transactionId: item.id,
          reference: item.reference,
        })
      }
      accessibilityRole="button"
      accessibilityLabel={`${item.reference} ${item.status}`}
    >
      <TransactionItem transaction={item} />
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.safe}>
      {/* App bar */}
      <View style={styles.appBar}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={styles.backText}>←</Text>
        </TouchableOpacity>
        <Text style={styles.appBarTitle}>{i18n.t('transactions.history_title')}</Text>
        <View style={{ width: 44 }} />
      </View>

      {/* Status filter tabs */}
      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.id}
            onPress={() => setStatusFilter(f.id)}
            style={[styles.filterTab, statusFilter === f.id && styles.filterTabActive]}
            accessibilityRole="tab"
            accessibilityState={{ selected: statusFilter === f.id }}
          >
            <Text
              style={[
                styles.filterTabText,
                statusFilter === f.id && styles.filterTabTextActive,
              ]}
            >
              {i18n.t(f.labelKey)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      {isLoading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.teal} />
        </View>
      ) : isError ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{i18n.t('errors.generic')}</Text>
          <TerahButton
            label={i18n.t('common.retry')}
            onPress={() => refetch()}
            style={{ marginTop: 16 }}
          />
        </View>
      ) : (
        <FlatList
          data={transactions}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={transactions.length === 0 ? styles.emptyContainer : undefined}
          refreshControl={
            <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.teal} />
          }
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>📋</Text>
              <Text style={styles.emptyText}>{i18n.t('transactions.history_empty')}</Text>
            </View>
          }
          style={styles.list}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.offWhite },
  appBar: {
    backgroundColor: colors.navy,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    height: 56,
  },
  backButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backText: { fontFamily: 'Poppins_600SemiBold', fontSize: 20, color: '#FFFFFF' },
  appBarTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 18,
    color: '#FFFFFF',
  },
  filterRow: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
    gap: spacing.sm,
  },
  filterTab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: radius.md,
    backgroundColor: 'transparent',
  },
  filterTabActive: { backgroundColor: colors.teal + '20' },
  filterTabText: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 12,
    color: colors.midGrey,
  },
  filterTabTextActive: {
    color: colors.teal,
    fontFamily: 'Roboto_500Medium',
  },
  list: { flex: 1 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontFamily: 'Roboto_400Regular', fontSize: 15, color: colors.error },
  emptyContainer: { flex: 1 },
  emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 80 },
  emptyIcon: { fontSize: 48, marginBottom: spacing.md },
  emptyText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.midGrey,
    textAlign: 'center',
  },
});
