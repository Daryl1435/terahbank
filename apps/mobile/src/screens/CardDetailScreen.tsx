/**
 * FR-029–033: Virtual VISA card detail view.
 *
 * Shows full details for a single card:
 *   - Card art (masked number, expiry, status badge)
 *   - Freeze / Unfreeze toggle (instant local optimistic update)
 *   - Spending limit editor (daily + per-transaction, inline)
 *   - Transaction history shortcut
 *
 * Navigated to from CardScreen when user taps a card tile.
 * PCI-DSS SAQ-A: only last_four + expiry displayed — raw PAN never stored.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  TextInput,
} from 'react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { useCards, useFreezeCard, useUnfreezeCard, useUpdateCardLimits } from '@/hooks/useCards';
import { TerahButton } from '@/components/TerahButton';
import { colors, spacing, radius } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';
import type { Card } from '@/services/cards';

type CardDetailNavProp  = NativeStackNavigationProp<RootStackParamList, 'CardDetail'>;
type CardDetailRouteProp = RouteProp<RootStackParamList, 'CardDetail'>;

interface CardDetailScreenProps {
  navigation: CardDetailNavProp;
  route: CardDetailRouteProp;
}

const STATUS_COLORS: Record<string, string> = {
  active:    colors.success,
  frozen:    colors.warning,
  expired:   colors.midGrey,
  cancelled: colors.error,
};

const STATUS_BG: Record<string, string> = {
  active:    colors.success + '22',
  frozen:    colors.warning + '22',
  expired:   colors.midGrey + '22',
  cancelled: colors.error + '22',
};

export default function CardDetailScreen({ navigation, route }: CardDetailScreenProps) {
  const { cardId } = route.params;

  const { data: cards, isLoading, refetch } = useCards();
  const card: Card | undefined = cards?.find((c) => c.card_id === cardId);

  const { mutateAsync: freeze, isPending: freezing }   = useFreezeCard();
  const { mutateAsync: unfreeze, isPending: unfreezing } = useUnfreezeCard();
  const { mutateAsync: updateLimits, isPending: updatingLimits } = useUpdateCardLimits();

  // Limit edit state
  const [editingLimits, setEditingLimits] = useState(false);
  const [dailyLimit,  setDailyLimit]  = useState('');
  const [perTxnLimit, setPerTxnLimit] = useState('');

  const openLimitEditor = () => {
    if (!card) return;
    setDailyLimit(card.daily_limit  != null ? String(card.daily_limit  / 100) : '');
    setPerTxnLimit(card.per_transaction_limit != null ? String(card.per_transaction_limit / 100) : '');
    setEditingLimits(true);
  };

  const handleSaveLimits = async () => {
    if (!card) return;
    const payload: { daily_limit?: number; per_transaction_limit?: number } = {};
    if (dailyLimit)   payload.daily_limit            = parseInt(dailyLimit, 10) * 100;
    if (perTxnLimit)  payload.per_transaction_limit  = parseInt(perTxnLimit, 10) * 100;
    if (!payload.daily_limit && !payload.per_transaction_limit) {
      setEditingLimits(false);
      return;
    }
    try {
      await updateLimits({ cardId: card.card_id, payload });
      setEditingLimits(false);
    } catch (err: any) {
      Alert.alert(i18n.t('cards.limit_error'), err?.message ?? i18n.t('errors.generic'));
    }
  };

  const handleFreezeToggle = async () => {
    if (!card) return;
    try {
      if (card.status === 'active') {
        await freeze(card.card_id);
      } else if (card.status === 'frozen') {
        await unfreeze(card.card_id);
      }
    } catch (err: any) {
      Alert.alert(i18n.t('cards.action_error'), err?.message ?? i18n.t('errors.generic'));
    }
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.safe}>
        <ActivityIndicator style={{ flex: 1 }} color={colors.teal} />
      </SafeAreaView>
    );
  }

  if (!card) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text style={styles.backText}>← {i18n.t('common.back')}</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.centered}>
          <Text style={styles.notFoundText}>{i18n.t('cards.card_not_found')}</Text>
        </View>
      </SafeAreaView>
    );
  }

  const canToggleFreeze = card.status === 'active' || card.status === 'frozen';
  const isBusy = freezing || unfreezing;
  const isInactive = card.status === 'expired' || card.status === 'cancelled';

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
        <Text style={styles.title}>{i18n.t('cards.detail_title')}</Text>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>

        {/* ── Card art ────────────────────────────────────────────────────── */}
        <View style={[styles.cardArt, card.status === 'frozen' && styles.cardArtFrozen]}>
          {/* VISA wordmark */}
          <Text style={styles.cardBrand}>VISA</Text>

          {/* Chip placeholder */}
          <View style={styles.chip} />

          {/* Masked number */}
          <Text style={styles.cardNumber}>
            •••• •••• •••• {card.last_four}
          </Text>

          <View style={styles.cardFooter}>
            <View>
              <Text style={styles.cardFieldLabel}>{i18n.t('cards.expires').toUpperCase()}</Text>
              <Text style={styles.cardFieldValue}>{card.expiry_date.substring(0, 7)}</Text>
            </View>
            {/* Status badge */}
            <View style={[styles.statusBadge, { backgroundColor: STATUS_BG[card.status] }]}>
              <Text style={[styles.statusText, { color: STATUS_COLORS[card.status] }]}>
                {i18n.t(`cards.status_${card.status}`)}
              </Text>
            </View>
          </View>

          {/* Frozen overlay */}
          {card.status === 'frozen' && (
            <View style={styles.frozenOverlay}>
              <Text style={styles.frozenIcon}>❄️</Text>
              <Text style={styles.frozenLabel}>{i18n.t('cards.frozen_label')}</Text>
            </View>
          )}
        </View>

        {/* ── Freeze / Unfreeze ────────────────────────────────────────────── */}
        {canToggleFreeze && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{i18n.t('cards.card_controls')}</Text>
            <TouchableOpacity
              onPress={handleFreezeToggle}
              disabled={isBusy}
              style={[
                styles.freezeRow,
                card.status === 'frozen' ? styles.freezeRowFrozen : styles.freezeRowActive,
              ]}
              accessibilityRole="button"
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.freezeTitle}>
                  {card.status === 'active' ? i18n.t('cards.freeze') : i18n.t('cards.unfreeze')}
                </Text>
                <Text style={styles.freezeSubtitle}>
                  {card.status === 'active'
                    ? i18n.t('cards.freeze_hint')
                    : i18n.t('cards.unfreeze_hint')}
                </Text>
              </View>
              {isBusy
                ? <ActivityIndicator color={colors.white} />
                : <Text style={styles.freezeChevron}>
                    {card.status === 'active' ? '❄️' : '▶'}
                  </Text>
              }
            </TouchableOpacity>
          </View>
        )}

        {/* ── Spending limits ──────────────────────────────────────────────── */}
        {!isInactive && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>{i18n.t('cards.spending_limits')}</Text>
              {!editingLimits && (
                <TouchableOpacity
                  onPress={openLimitEditor}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={styles.editLink}>{i18n.t('common.edit')}</Text>
                </TouchableOpacity>
              )}
            </View>

            {editingLimits ? (
              <View style={styles.limitsEditor}>
                <Text style={styles.limitLabel}>{i18n.t('cards.daily_limit')} (XAF)</Text>
                <TextInput
                  value={dailyLimit}
                  onChangeText={(t) => setDailyLimit(t.replace(/[^0-9]/g, ''))}
                  keyboardType="numeric"
                  placeholder={i18n.t('cards.limit_placeholder')}
                  placeholderTextColor={colors.midGrey}
                  style={styles.limitInput}
                />
                <Text style={[styles.limitLabel, { marginTop: spacing.sm }]}>
                  {i18n.t('cards.per_txn_limit')} (XAF)
                </Text>
                <TextInput
                  value={perTxnLimit}
                  onChangeText={(t) => setPerTxnLimit(t.replace(/[^0-9]/g, ''))}
                  keyboardType="numeric"
                  placeholder={i18n.t('cards.limit_placeholder')}
                  placeholderTextColor={colors.midGrey}
                  style={styles.limitInput}
                />
                <View style={styles.limitsEditorActions}>
                  <TerahButton
                    label={updatingLimits ? i18n.t('common.loading') : i18n.t('common.save')}
                    onPress={handleSaveLimits}
                    loading={updatingLimits}
                    disabled={updatingLimits}
                    style={{ flex: 1, marginRight: 8 }}
                  />
                  <TouchableOpacity
                    onPress={() => setEditingLimits(false)}
                    style={styles.cancelBtn}
                    disabled={updatingLimits}
                  >
                    <Text style={styles.cancelBtnText}>{i18n.t('common.cancel')}</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              <View style={styles.limitsDisplay}>
                <View style={styles.limitRow}>
                  <Text style={styles.limitRowLabel}>{i18n.t('cards.daily_limit')}</Text>
                  <Text style={styles.limitRowValue}>
                    {card.daily_limit != null ? formatXAF(card.daily_limit) : i18n.t('cards.no_limit')}
                  </Text>
                </View>
                <View style={[styles.limitRow, { borderBottomWidth: 0 }]}>
                  <Text style={styles.limitRowLabel}>{i18n.t('cards.per_txn_limit')}</Text>
                  <Text style={styles.limitRowValue}>
                    {card.per_transaction_limit != null
                      ? formatXAF(card.per_transaction_limit)
                      : i18n.t('cards.no_limit')}
                  </Text>
                </View>
              </View>
            )}
          </View>
        )}

        {/* ── Transaction history ──────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('cards.transaction_history')}</Text>
          <TouchableOpacity
            onPress={() =>
              navigation.navigate('TransactionHistory', { accountId: card.account_id })
            }
            style={styles.historyRow}
            accessibilityRole="button"
          >
            <Text style={styles.historyRowText}>{i18n.t('cards.view_all_transactions')}</Text>
            <Text style={styles.historyChevron}>›</Text>
          </TouchableOpacity>
        </View>

        {/* ── Card meta ────────────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('cards.card_info')}</Text>
          <View style={styles.metaCard}>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>{i18n.t('cards.card_id_label')}</Text>
              <Text style={styles.metaValue} numberOfLines={1} ellipsizeMode="middle">
                {card.card_id}
              </Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>{i18n.t('cards.issued_on')}</Text>
              <Text style={styles.metaValue}>
                {new Date(card.created_at).toLocaleDateString('fr-FR')}
              </Text>
            </View>
          </View>
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:       { flex: 1, backgroundColor: colors.offWhite },
  scroll:     { flex: 1 },
  container:  { paddingHorizontal: spacing.md, paddingBottom: 40 },
  centered:   { flex: 1, alignItems: 'center', justifyContent: 'center' },
  notFoundText: { fontFamily: 'Roboto_400Regular', fontSize: 16, color: colors.midGrey },

  header: {
    paddingHorizontal: spacing.md,
    paddingTop:        spacing.lg,
    paddingBottom:     spacing.md,
  },
  backButton: {
    minHeight:  44,
    alignSelf:  'flex-start',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  backText: { fontFamily: 'Roboto_500Medium', fontSize: 14, color: colors.teal },
  title:    { fontFamily: 'Poppins_700Bold', fontSize: 24, color: colors.navy },

  // Card art
  cardArt: {
    backgroundColor: colors.navy,
    borderRadius:    radius.xl,
    padding:         spacing.lg,
    marginBottom:    spacing.lg,
    minHeight:       200,
    position:        'relative',
    overflow:        'hidden',
  },
  cardArtFrozen: { opacity: 0.75 },
  cardBrand: {
    fontFamily: 'Poppins_700Bold',
    fontSize:   22,
    color:      colors.white,
    letterSpacing: 2,
    alignSelf:  'flex-end',
    marginBottom: spacing.md,
  },
  chip: {
    width:           40,
    height:          30,
    borderRadius:    5,
    backgroundColor: colors.teal,
    marginBottom:    spacing.lg,
  },
  cardNumber: {
    fontFamily:    'Poppins_600SemiBold',
    fontSize:      22,
    color:         colors.white,
    letterSpacing: 3,
    marginBottom:  spacing.lg,
  },
  cardFooter: {
    flexDirection:  'row',
    justifyContent: 'space-between',
    alignItems:     'flex-end',
  },
  cardFieldLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize:   10,
    color:      'rgba(255,255,255,0.6)',
    letterSpacing: 1,
  },
  cardFieldValue: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize:   15,
    color:      colors.white,
    marginTop:  2,
  },
  statusBadge: {
    borderRadius:      12,
    paddingHorizontal: 12,
    paddingVertical:   4,
  },
  statusText: { fontFamily: 'Roboto_500Medium', fontSize: 12 },

  // Frozen overlay
  frozenOverlay: {
    position:       'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    alignItems:     'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.25)',
  },
  frozenIcon:  { fontSize: 40, marginBottom: 8 },
  frozenLabel: { fontFamily: 'Poppins_700Bold', fontSize: 18, color: colors.white },

  // Sections
  section: {
    backgroundColor: colors.white,
    borderRadius:    radius.lg,
    padding:         spacing.md,
    marginBottom:    spacing.sm,
  },
  sectionHeader: {
    flexDirection:  'row',
    justifyContent: 'space-between',
    alignItems:     'center',
    marginBottom:   spacing.md,
  },
  sectionTitle: {
    fontFamily:   'Poppins_600SemiBold',
    fontSize:     14,
    color:        colors.navy,
    marginBottom: spacing.md,
  },
  editLink: { fontFamily: 'Roboto_500Medium', fontSize: 13, color: colors.teal },

  // Freeze toggle
  freezeRow: {
    flexDirection:  'row',
    alignItems:     'center',
    borderRadius:   radius.md,
    padding:        spacing.md,
  },
  freezeRowActive: { backgroundColor: colors.warning + '18' },
  freezeRowFrozen: { backgroundColor: colors.success + '18' },
  freezeTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize:   15,
    color:      colors.navy,
    marginBottom: 2,
  },
  freezeSubtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize:   12,
    color:      colors.midGrey,
  },
  freezeChevron: { fontSize: 22, marginLeft: spacing.sm },

  // Limits
  limitsDisplay: {},
  limitRow: {
    flexDirection:     'row',
    justifyContent:    'space-between',
    alignItems:        'center',
    paddingVertical:   10,
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
  },
  limitRowLabel: { fontFamily: 'Roboto_400Regular', fontSize: 14, color: colors.midGrey },
  limitRowValue: { fontFamily: 'Poppins_600SemiBold', fontSize: 14, color: colors.navy },

  limitsEditor: {},
  limitLabel: { fontFamily: 'Roboto_500Medium', fontSize: 13, color: colors.darkGrey, marginBottom: 6 },
  limitInput: {
    backgroundColor:   colors.offWhite,
    borderRadius:      radius.md,
    borderWidth:       1,
    borderColor:       colors.lightGrey,
    paddingHorizontal: spacing.md,
    height:            52,
    fontFamily:        'Roboto_400Regular',
    fontSize:          16,
    color:             colors.darkGrey,
  },
  limitsEditorActions: {
    flexDirection:  'row',
    alignItems:     'center',
    marginTop:      spacing.md,
  },
  cancelBtn: {
    height:         44,
    paddingHorizontal: spacing.md,
    alignItems:     'center',
    justifyContent: 'center',
  },
  cancelBtnText: { fontFamily: 'Roboto_500Medium', fontSize: 14, color: colors.midGrey },

  // Transaction history link
  historyRow: {
    flexDirection:  'row',
    alignItems:     'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    minHeight:      44,
  },
  historyRowText: { fontFamily: 'Roboto_500Medium', fontSize: 15, color: colors.teal },
  historyChevron: { fontSize: 22, color: colors.midGrey },

  // Meta
  metaCard: {},
  metaRow: {
    flexDirection:     'row',
    justifyContent:    'space-between',
    alignItems:        'center',
    paddingVertical:   8,
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
  },
  metaLabel: { fontFamily: 'Roboto_400Regular', fontSize: 13, color: colors.midGrey },
  metaValue: { fontFamily: 'Roboto_500Medium', fontSize: 13, color: colors.darkGrey, maxWidth: '60%' },
});
