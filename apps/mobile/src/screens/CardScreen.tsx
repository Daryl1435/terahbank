/**
 * FR-029–033: Virtual VISA card list screen.
 *
 * Shows all cards for the user. Tapping a card navigates to CardDetailScreen.
 * Issue new card FAB at the bottom — picks a Standard Account → POST /cards.
 * Max cards enforced server-side (FR-033); 422 CARD_LIMIT_REACHED shown as alert.
 *
 * PCI-DSS SAQ-A: raw card numbers never stored or displayed — only last_four + expiry.
 */
import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  RefreshControl,
} from 'react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { useCards, useIssueCard } from '@/hooks/useCards';
import { useTotalBalance } from '@/hooks/useBalance';
import { TerahButton } from '@/components/TerahButton';
import { colors, spacing, radius } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';
import type { Card } from '@/services/cards';

type CardNavProp = NativeStackNavigationProp<RootStackParamList>;

interface CardScreenProps {
  navigation: CardNavProp;
  route?: any;
}

const STATUS_COLORS: Record<string, string> = {
  active:    colors.success,
  frozen:    colors.warning,
  expired:   colors.midGrey,
  cancelled: colors.error,
};

export default function CardScreen({ navigation }: CardScreenProps) {
  const { data: cards, isLoading, refetch, isRefetching } = useCards();
  const { accounts } = useTotalBalance();
  const { mutateAsync: issueCard, isPending: issuing } = useIssueCard();

  const standardAccounts = accounts?.filter((a) => a.account_type === 'standard') ?? [];

  const handleIssueCard = () => {
    if (standardAccounts.length === 0) {
      Alert.alert(i18n.t('cards.no_standard_account'));
      return;
    }
    const account = standardAccounts[0];
    Alert.alert(
      i18n.t('cards.issue_confirm_title'),
      i18n.t('cards.issue_confirm_message'),
      [
        { text: i18n.t('common.cancel'), style: 'cancel' },
        {
          text: i18n.t('cards.issue_confirm_cta'),
          onPress: async () => {
            try {
              await issueCard({ account_id: account.account_id });
              Alert.alert(i18n.t('cards.issue_success'));
            } catch (err: any) {
              Alert.alert(i18n.t('cards.issue_error'), err?.message ?? i18n.t('errors.generic'));
            }
          },
        },
      ],
    );
  };

  const renderCard = (card: Card) => (
    <TouchableOpacity
      key={card.card_id}
      onPress={() => navigation.navigate('CardDetail', { cardId: card.card_id })}
      style={styles.cardTile}
      accessibilityRole="button"
      activeOpacity={0.75}
    >
      {/* Left: visual chip + number */}
      <View style={[styles.cardVisual, card.status === 'frozen' && styles.cardVisualFrozen]}>
        <View style={styles.chip} />
        <Text style={styles.cardNumber}>•••• {card.last_four}</Text>
      </View>

      {/* Right: meta + status */}
      <View style={styles.cardMeta}>
        <View style={styles.cardMetaTop}>
          <Text style={styles.cardExpiry}>
            {i18n.t('cards.expires')} {card.expiry_date.substring(0, 7)}
          </Text>
          <View style={[styles.statusBadge, { backgroundColor: STATUS_COLORS[card.status] + '22' }]}>
            <Text style={[styles.statusText, { color: STATUS_COLORS[card.status] }]}>
              {i18n.t(`cards.status_${card.status}`)}
            </Text>
          </View>
        </View>

        <View style={styles.limitsRow}>
          <View style={styles.limitItem}>
            <Text style={styles.limitLabel}>{i18n.t('cards.daily_limit')}</Text>
            <Text style={styles.limitValue}>
              {card.daily_limit != null ? formatXAF(card.daily_limit) : i18n.t('cards.no_limit')}
            </Text>
          </View>
          <View style={styles.limitItem}>
            <Text style={styles.limitLabel}>{i18n.t('cards.per_txn_limit')}</Text>
            <Text style={styles.limitValue}>
              {card.per_transaction_limit != null
                ? formatXAF(card.per_transaction_limit)
                : i18n.t('cards.no_limit')}
            </Text>
          </View>
        </View>
      </View>

      <Text style={styles.chevron}>›</Text>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={styles.backText}>← {i18n.t('common.back')}</Text>
        </TouchableOpacity>
        <Text style={styles.title}>{i18n.t('cards.title')}</Text>
        <Text style={styles.subtitle}>{i18n.t('cards.list_subtitle')}</Text>
      </View>

      {isLoading ? (
        <ActivityIndicator style={{ flex: 1 }} color={colors.teal} />
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.container}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
        >
          {cards && cards.length > 0 ? (
            cards.map(renderCard)
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>💳</Text>
              <Text style={styles.emptyTitle}>{i18n.t('cards.empty_title')}</Text>
              <Text style={styles.emptyMessage}>{i18n.t('cards.empty_message')}</Text>
            </View>
          )}
        </ScrollView>
      )}

      {/* Issue card CTA */}
      <View style={styles.fabWrapper}>
        <TerahButton
          label={issuing ? i18n.t('common.loading') : i18n.t('cards.issue_cta')}
          onPress={handleIssueCard}
          loading={issuing}
          disabled={issuing}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:       { flex: 1, backgroundColor: colors.offWhite },
  scroll:     { flex: 1 },
  container:  { paddingHorizontal: spacing.md, paddingBottom: 100 },
  header: {
    paddingHorizontal: spacing.md,
    paddingTop:        spacing.lg,
    paddingBottom:     spacing.md,
  },
  backButton:  { minHeight: 44, alignSelf: 'flex-start', justifyContent: 'center', marginBottom: spacing.sm },
  backText:    { fontFamily: 'Roboto_500Medium', fontSize: 14, color: colors.teal },
  title:       { fontFamily: 'Poppins_700Bold', fontSize: 24, color: colors.navy },
  subtitle:    { fontFamily: 'Roboto_400Regular', fontSize: 13, color: colors.midGrey, marginTop: 4 },

  cardTile: {
    backgroundColor: colors.white,
    borderRadius:    radius.lg,
    padding:         spacing.md,
    marginBottom:    spacing.sm,
    flexDirection:   'row',
    alignItems:      'center',
  },
  cardVisual: {
    backgroundColor: colors.navy,
    borderRadius:    radius.md,
    padding:         spacing.sm,
    width:           80,
    height:          52,
    justifyContent:  'space-between',
    marginRight:     spacing.md,
  },
  cardVisualFrozen: { opacity: 0.55 },
  chip: {
    width:           20,
    height:          14,
    borderRadius:    3,
    backgroundColor: colors.teal,
  },
  cardNumber: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize:   10,
    color:      colors.white,
    letterSpacing: 1,
  },

  cardMeta:    { flex: 1 },
  cardMetaTop: {
    flexDirection:  'row',
    alignItems:     'center',
    justifyContent: 'space-between',
    marginBottom:   spacing.xs,
  },
  cardExpiry: {
    fontFamily: 'Roboto_400Regular',
    fontSize:   12,
    color:      colors.midGrey,
  },
  statusBadge: { borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 },
  statusText:  { fontFamily: 'Roboto_500Medium', fontSize: 11 },

  limitsRow:  { flexDirection: 'row', gap: 12 },
  limitItem:  {},
  limitLabel: { fontFamily: 'Roboto_400Regular', fontSize: 11, color: colors.midGrey },
  limitValue: { fontFamily: 'Poppins_600SemiBold', fontSize: 12, color: colors.navy, marginTop: 1 },

  chevron: { fontSize: 22, color: colors.lightGrey, marginLeft: spacing.sm },

  emptyState: { alignItems: 'center', paddingTop: 80 },
  emptyIcon:  { fontSize: 56, marginBottom: spacing.md },
  emptyTitle: { fontFamily: 'Poppins_600SemiBold', fontSize: 18, color: colors.navy, marginBottom: 8 },
  emptyMessage: {
    fontFamily: 'Roboto_400Regular',
    fontSize:   14,
    color:      colors.midGrey,
    textAlign:  'center',
    lineHeight: 22,
    paddingHorizontal: spacing.lg,
  },

  fabWrapper: { padding: spacing.md, backgroundColor: colors.offWhite },
});
