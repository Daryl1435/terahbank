/**
 * FR-038: Deposit flow — MTN MoMo channel (3.3/3.4 channels shown as coming soon).
 *
 * Step 1 — Channel selection (MTN MoMo active; Orange/Card disabled)
 * Step 2 — Account selection + amount entry (in XAF; converted to units × 100)
 * Step 3 — Confirmation summary → POST /transactions/deposit → navigate to status
 *
 * UC-003: Backend returns 202 immediately. Status tracked via TransactionDetailScreen polling.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { useDeposit } from '@/hooks/useTransactions';
import { useTotalBalance } from '@/hooks/useBalance';
import { TerahButton } from '@/components/TerahButton';
import { ChannelLogo } from '@/components/ChannelLogo';
import type { PaymentChannel } from '@/components/ChannelLogo';
import { colors, spacing, radius } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';

type DepositNavProp = NativeStackNavigationProp<RootStackParamList, 'Deposit'>;

interface DepositScreenProps {
  navigation: DepositNavProp;
}

type Channel = 'mtn_momo' | 'orange_money' | 'visa';
type Step = 1 | 2 | 3;

const CHANNELS: Array<{ id: Channel; labelKey: string; active: boolean }> = [
  { id: 'mtn_momo',     labelKey: 'transactions.deposit_channel_momo',   active: true },
  { id: 'orange_money', labelKey: 'transactions.deposit_channel_orange',  active: true },
  { id: 'visa',         labelKey: 'transactions.deposit_channel_card',    active: true },
];

export default function DepositScreen({ navigation }: DepositScreenProps) {
  const [step, setStep] = useState<Step>(1);
  const [selectedChannel, setSelectedChannel] = useState<Channel>('mtn_momo');
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [amountXAF, setAmountXAF] = useState('');
  const [amountError, setAmountError] = useState<string | null>(null);

  const { accounts, isLoading: accountsLoading } = useTotalBalance();
  const { mutateAsync: deposit, isPending } = useDeposit();

  // Set default account on first load
  React.useEffect(() => {
    if (accounts && accounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(accounts[0].account_id);
    }
  }, [accounts]);

  const selectedAccount = accounts?.find((a) => a.account_id === selectedAccountId);

  const validateAmount = (): boolean => {
    const xaf = parseInt(amountXAF.replace(/\s/g, ''), 10);
    if (isNaN(xaf) || xaf <= 0) {
      setAmountError(i18n.t('transactions.amount_invalid'));
      return false;
    }
    if (xaf < 1) {
      setAmountError(i18n.t('transactions.amount_too_low'));
      return false;
    }
    setAmountError(null);
    return true;
  };

  const handleAmountNext = () => {
    if (!selectedAccountId) return;
    if (validateAmount()) setStep(3);
  };

  const handleSubmit = async () => {
    const xaf = parseInt(amountXAF.replace(/\s/g, ''), 10);
    const amountUnits = xaf * 100;   // XAF → smallest unit

    try {
      const txn = await deposit({
        account_id: selectedAccountId,
        amount: amountUnits,
        channel: selectedChannel,
      });
      // Card channels: open hosted payment page in WebView
      if (selectedChannel === 'visa') {
        navigation.replace('CardPaymentWebView', {
          paymentUrl: (txn as any).payment_url ?? '',
          transactionId: (txn as any).transaction_id ?? '',
          reference: (txn as any).reference,
        });
        return;
      }
      // MoMo/Orange: navigate to status polling screen (202 accepted — payment is async)
      navigation.replace('TransactionDetail', {
        transactionId: (txn as any).transaction_id ?? '',
        reference: (txn as any).reference,
      });
    } catch (err: any) {
      Alert.alert(
        i18n.t('transactions.deposit_failed'),
        err?.message ?? i18n.t('errors.generic'),
      );
    }
  };

  const renderHeader = () => (
    <View style={styles.header}>
      <TouchableOpacity
        onPress={() => (step > 1 ? setStep((s) => (s - 1) as Step) : navigation.goBack())}
        style={styles.backButton}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('common.back')}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Text style={styles.backText}>← {i18n.t('common.back')}</Text>
      </TouchableOpacity>
      <Text style={styles.title}>{i18n.t('transactions.deposit_title')}</Text>
      <Text style={styles.stepIndicator}>
        {i18n.t('transactions.step_of', { step, total: 3 })}
      </Text>
    </View>
  );

  // ── Step 1: Channel selection ──────────────────────────────────────────────
  if (step === 1) {
    return (
      <SafeAreaView style={styles.safe}>
        <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
          {renderHeader()}
          <Text style={styles.sectionTitle}>
            {i18n.t('transactions.deposit_channel_title')}
          </Text>

          {CHANNELS.map((ch) => (
            <TouchableOpacity
              key={ch.id}
              onPress={() => ch.active && setSelectedChannel(ch.id)}
              disabled={!ch.active}
              activeOpacity={ch.active ? 0.7 : 1}
              style={[
                styles.channelCard,
                selectedChannel === ch.id && styles.channelCardSelected,
                !ch.active && styles.channelCardDisabled,
              ]}
              accessibilityRole="radio"
              accessibilityState={{ selected: selectedChannel === ch.id, disabled: !ch.active }}
            >
              <View style={{ marginRight: spacing.md }}>
                <ChannelLogo channel={ch.id as PaymentChannel} size={40} />
              </View>
              <View style={styles.channelInfo}>
                <Text style={[styles.channelLabel, !ch.active && styles.channelLabelDisabled]}>
                  {i18n.t(ch.labelKey)}
                </Text>
                {!ch.active && (
                  <Text style={styles.comingSoon}>
                    {i18n.t('transactions.deposit_channel_coming_soon')}
                  </Text>
                )}
              </View>
              {ch.active && (
                <View style={[
                  styles.radioCircle,
                  selectedChannel === ch.id && styles.radioCircleSelected,
                ]}>
                  {selectedChannel === ch.id && <View style={styles.radioDot} />}
                </View>
              )}
            </TouchableOpacity>
          ))}

          <TerahButton
            label={i18n.t('common.continue')}
            onPress={() => setStep(2)}
            style={styles.cta}
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ── Step 2: Account + amount ───────────────────────────────────────────────
  if (step === 2) {
    return (
      <SafeAreaView style={styles.safe}>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView style={styles.screen} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
            {renderHeader()}
          <Text style={styles.sectionTitle}>
            {i18n.t('transactions.deposit_amount_title')}
          </Text>

          {/* Account selector */}
          <Text style={styles.fieldLabel}>{i18n.t('transactions.select_account')}</Text>
          {accountsLoading ? (
            <ActivityIndicator color={colors.teal} style={{ marginVertical: 16 }} />
          ) : (
            accounts?.map((acct) => (
              <TouchableOpacity
                key={acct.account_id}
                onPress={() => setSelectedAccountId(acct.account_id)}
                style={[
                  styles.accountOption,
                  selectedAccountId === acct.account_id && styles.accountOptionSelected,
                ]}
                accessibilityRole="radio"
                accessibilityState={{ selected: selectedAccountId === acct.account_id }}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.accountName}>
                    {i18n.t(`accounts.${acct.account_type}`)}
                  </Text>
                  <Text style={styles.accountBalance}>{formatXAF(acct.balance)}</Text>
                </View>
                <View style={[
                  styles.radioCircle,
                  selectedAccountId === acct.account_id && styles.radioCircleSelected,
                ]}>
                  {selectedAccountId === acct.account_id && <View style={styles.radioDot} />}
                </View>
              </TouchableOpacity>
            ))
          )}

          {/* Amount input */}
          <Text style={[styles.fieldLabel, { marginTop: spacing.md }]}>
            {i18n.t('transactions.deposit_amount_label')}
          </Text>
          <View style={[styles.amountInputWrapper, amountError ? styles.inputError : null]}>
            <Text style={styles.currencyPrefix}>XAF</Text>
            <TextInput
              value={amountXAF}
              onChangeText={(t) => {
                setAmountXAF(t.replace(/[^0-9]/g, ''));
                setAmountError(null);
              }}
              keyboardType="numeric"
              placeholder={i18n.t('transactions.deposit_amount_placeholder')}
              placeholderTextColor={colors.midGrey}
              style={styles.amountInput}
              accessibilityLabel={i18n.t('transactions.deposit_amount_label')}
            />
          </View>
          {amountError ? (
            <Text style={styles.errorText}>{amountError}</Text>
          ) : (
            <Text style={styles.hintText}>{i18n.t('transactions.deposit_amount_hint')}</Text>
          )}

          <TerahButton
              label={i18n.t('common.continue')}
              onPress={handleAmountNext}
              disabled={!selectedAccountId || !amountXAF}
              style={styles.cta}
            />
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  // ── Step 3: Confirmation ───────────────────────────────────────────────────
  const xaf = parseInt(amountXAF.replace(/\s/g, ''), 10) || 0;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
        {renderHeader()}
        <Text style={styles.sectionTitle}>{i18n.t('transactions.deposit_confirm_title')}</Text>

        <View style={styles.summaryCard}>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryKey}>{i18n.t('transactions.deposit_confirm_account')}</Text>
            <Text style={styles.summaryValue}>
              {selectedAccount ? i18n.t(`accounts.${selectedAccount.account_type}`) : '—'}
            </Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryKey}>{i18n.t('transactions.deposit_confirm_amount')}</Text>
            <Text style={[styles.summaryValue, styles.summaryAmount]}>
              {formatXAF(xaf * 100)}
            </Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryKey}>{i18n.t('transactions.deposit_confirm_channel')}</Text>
            <Text style={styles.summaryValue}>
              {i18n.t(`transactions.deposit_channel_${selectedChannel === 'mtn_momo' ? 'momo' : selectedChannel === 'orange_money' ? 'orange' : 'card'}`)}
            </Text>
          </View>
        </View>

        <View style={styles.infoBanner}>
          <Text style={styles.infoText}>{i18n.t('transactions.deposit_confirm_prompt')}</Text>
        </View>

        <TerahButton
          label={isPending ? i18n.t('common.loading') : i18n.t('transactions.deposit_submit')}
          onPress={handleSubmit}
          loading={isPending}
          disabled={isPending}
          style={styles.cta}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.offWhite },
  screen: { flex: 1, backgroundColor: colors.offWhite },
  container: { paddingHorizontal: spacing.md, paddingBottom: 40 },
  header: { paddingTop: spacing.lg, paddingBottom: spacing.md },
  backButton: {
    minHeight: 44,
    alignSelf: 'flex-start',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  backText: { fontFamily: 'Roboto_500Medium', fontSize: 14, color: colors.teal },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 4,
  },
  stepIndicator: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
  },
  sectionTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 16,
    color: colors.navy,
    marginBottom: spacing.md,
  },
  channelCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  channelCardSelected: { borderColor: colors.teal },
  channelCardDisabled: { opacity: 0.5 },
  channelIcon: { marginRight: spacing.md },
  channelInfo: { flex: 1 },
  channelLabel: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: colors.navy,
  },
  channelLabelDisabled: { color: colors.midGrey },
  comingSoon: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    marginTop: 2,
  },
  radioCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.lightGrey,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioCircleSelected: { borderColor: colors.teal },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.teal,
  },
  fieldLabel: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.darkGrey,
    marginBottom: spacing.sm,
  },
  accountOption: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  accountOptionSelected: { borderColor: colors.teal },
  accountName: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.navy,
  },
  accountBalance: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    marginTop: 2,
  },
  amountInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.lightGrey,
    paddingHorizontal: spacing.md,
    height: 56,
    marginBottom: 4,
  },
  inputError: { borderColor: colors.error },
  currencyPrefix: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 16,
    color: colors.navy,
    marginRight: 10,
  },
  amountInput: {
    flex: 1,
    fontFamily: 'Roboto_400Regular',
    fontSize: 20,
    color: colors.darkGrey,
    paddingVertical: 0,
  },
  hintText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    marginBottom: spacing.md,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.error,
    marginBottom: spacing.md,
  },
  summaryCard: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
  },
  summaryKey: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
  },
  summaryValue: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.darkGrey,
  },
  summaryAmount: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 18,
    color: colors.navy,
  },
  infoBanner: {
    backgroundColor: colors.teal + '18',
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  infoText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.navy,
    lineHeight: 20,
  },
  cta: { marginTop: spacing.md },
});
