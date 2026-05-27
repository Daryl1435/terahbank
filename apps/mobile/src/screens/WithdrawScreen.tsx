/**
 * FR-039: Withdrawal flow — MTN MoMo and Orange Money channels.
 *
 * Step 1 — Channel selection (MTN MoMo, Orange Money)
 * Step 2 — Account selection + amount entry + destination phone (XAF → units × 100)
 * Step 3 — PIN confirmation → POST /transactions/withdraw → navigate to status polling
 *
 * Backend returns 202 immediately. Status tracked via TransactionDetailScreen polling.
 * Account is debited atomically before worker dispatches to MoMo API.
 * On API failure, worker issues a compensating credit (automatic rollback).
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { useWithdraw } from '@/hooks/useTransactions';
import { useTotalBalance } from '@/hooks/useBalance';
import { PINKeypad } from '@/components/PINKeypad';
import { TerahButton } from '@/components/TerahButton';
import { ChannelLogo } from '@/components/ChannelLogo';
import type { PaymentChannel } from '@/components/ChannelLogo';
import { colors, spacing, radius } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import { authService } from '@/services/auth';
import i18n from '@/locales';

type WithdrawNavProp = NativeStackNavigationProp<RootStackParamList, 'Withdraw'>;

interface WithdrawScreenProps {
  navigation: WithdrawNavProp;
}

type Channel = 'mtn_momo' | 'orange_money';
type Step = 1 | 2 | 3;

const CHANNELS: Array<{ id: Channel; labelKey: string }> = [
  { id: 'mtn_momo',     labelKey: 'transactions.deposit_channel_momo'  },
  { id: 'orange_money', labelKey: 'transactions.deposit_channel_orange' },
];

const CHANNEL_LABEL_KEY: Record<Channel, string> = {
  mtn_momo:     'transactions.deposit_channel_momo',
  orange_money: 'transactions.deposit_channel_orange',
};

export default function WithdrawScreen({ navigation }: WithdrawScreenProps) {
  const [step, setStep]                   = useState<Step>(1);
  const [selectedChannel, setSelectedChannel] = useState<Channel>('mtn_momo');
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [amountXAF, setAmountXAF]         = useState('');
  const [amountError, setAmountError]     = useState<string | null>(null);
  const [phone, setPhone]                 = useState('');
  const [phoneError, setPhoneError]       = useState<string | null>(null);
  const [pin, setPin]                     = useState('');
  const [pinError, setPinError]           = useState<string | null>(null);
  const [pinVerifying, setPinVerifying]   = useState(false);

  const { accounts, isLoading: accountsLoading } = useTotalBalance();
  const { mutateAsync: withdraw, isPending } = useWithdraw();

  React.useEffect(() => {
    if (accounts && accounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(accounts[0].account_id);
    }
  }, [accounts]);

  const selectedAccount = accounts?.find((a) => a.account_id === selectedAccountId);

  const renderHeader = (currentStep: number) => (
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
      <Text style={styles.title}>{i18n.t('transactions.withdraw_title')}</Text>
      <Text style={styles.stepIndicator}>
        {i18n.t('transactions.step_of', { step: currentStep, total: 3 })}
      </Text>
    </View>
  );

  // ── Step 1: Channel selection ──────────────────────────────────────────────
  if (step === 1) {
    return (
      <SafeAreaView style={styles.safe}>
        <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
          {renderHeader(1)}
          <Text style={styles.sectionTitle}>
            {i18n.t('transactions.withdraw_channel_title')}
          </Text>

          {CHANNELS.map((ch) => (
            <TouchableOpacity
              key={ch.id}
              onPress={() => setSelectedChannel(ch.id)}
              activeOpacity={0.7}
              style={[
                styles.channelCard,
                selectedChannel === ch.id && styles.channelCardSelected,
              ]}
              accessibilityRole="radio"
              accessibilityState={{ selected: selectedChannel === ch.id }}
            >
              <View style={{ marginRight: spacing.md }}>
                <ChannelLogo channel={ch.id as PaymentChannel} size={40} />
              </View>
              <View style={styles.channelInfo}>
                <Text style={styles.channelLabel}>{i18n.t(ch.labelKey)}</Text>
              </View>
              <View style={[
                styles.radioCircle,
                selectedChannel === ch.id && styles.radioCircleSelected,
              ]}>
                {selectedChannel === ch.id && <View style={styles.radioDot} />}
              </View>
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

  // ── Step 2: Account + amount + destination phone ───────────────────────────

  const handleAmountNext = () => {
    const xaf = parseInt(amountXAF.replace(/\s/g, ''), 10);
    let valid = true;

    if (isNaN(xaf) || xaf <= 0) {
      setAmountError(i18n.t('transactions.amount_invalid'));
      valid = false;
    } else {
      setAmountError(null);
    }

    const trimmedPhone = phone.trim();
    if (!trimmedPhone || !trimmedPhone.startsWith('+')) {
      setPhoneError(i18n.t('transactions.withdraw_phone_placeholder'));
      valid = false;
    } else {
      setPhoneError(null);
    }

    if (valid && selectedAccountId) setStep(3);
  };

  if (step === 2) {
    return (
      <SafeAreaView style={styles.safe}>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView style={styles.screen} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
            {renderHeader(2)}
          <Text style={styles.sectionTitle}>
            {i18n.t('transactions.withdraw_amount_title')}
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
            {i18n.t('transactions.withdraw_amount_label')}
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
              placeholder={i18n.t('transactions.withdraw_amount_placeholder')}
              placeholderTextColor={colors.midGrey}
              style={styles.amountInput}
              accessibilityLabel={i18n.t('transactions.withdraw_amount_label')}
            />
          </View>
          {amountError ? (
            <Text style={styles.errorText}>{amountError}</Text>
          ) : (
            <Text style={styles.hintText}>{i18n.t('transactions.withdraw_amount_hint')}</Text>
          )}

          {/* Destination phone */}
          <Text style={[styles.fieldLabel, { marginTop: spacing.md }]}>
            {i18n.t('transactions.withdraw_phone_label')}
          </Text>
          <View style={[styles.amountInputWrapper, phoneError ? styles.inputError : null]}>
            <TextInput
              value={phone}
              onChangeText={(t) => {
                setPhone(t);
                setPhoneError(null);
              }}
              keyboardType="phone-pad"
              placeholder={i18n.t('transactions.withdraw_phone_placeholder')}
              placeholderTextColor={colors.midGrey}
              style={[styles.amountInput, { flex: 1 }]}
              accessibilityLabel={i18n.t('transactions.withdraw_phone_label')}
            />
          </View>
          {phoneError ? (
            <Text style={styles.errorText}>{phoneError}</Text>
          ) : (
            <Text style={styles.hintText}>{i18n.t('transactions.withdraw_phone_hint')}</Text>
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

  // ── Step 3: PIN confirmation ───────────────────────────────────────────────
  const xaf = parseInt(amountXAF.replace(/\s/g, ''), 10) || 0;

  const handleSubmit = async () => {
    if (pin.length < 4) return;
    setPinVerifying(true);
    setPinError(null);

    let pinToken: string;
    try {
      const res = await authService.verifyPin(pin);
      pinToken = res.pin_token;
    } catch {
      setPinError(i18n.t('auth.pin_invalid'));
      setPin('');
      setPinVerifying(false);
      return;
    }

    try {
      const txn = await withdraw({
        account_id: selectedAccountId,
        amount: xaf * 100,
        channel: selectedChannel,
        destination_phone: phone.trim(),
        pin_token: pinToken,
      });
      navigation.replace('TransactionDetail', {
        transactionId: (txn as any).transaction_id ?? '',
        reference: (txn as any).reference,
      });
    } catch (err: any) {
      Alert.alert(
        i18n.t('transactions.withdraw_failed'),
        err?.message ?? i18n.t('errors.generic'),
      );
    } finally {
      setPinVerifying(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
        {renderHeader(3)}

        {/* Summary card */}
        <Text style={styles.sectionTitle}>
          {i18n.t('transactions.withdraw_confirm_title')}
        </Text>
        <View style={styles.summaryCard}>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryKey}>{i18n.t('transactions.withdraw_confirm_account')}</Text>
            <Text style={styles.summaryValue}>
              {selectedAccount ? i18n.t(`accounts.${selectedAccount.account_type}`) : '—'}
            </Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryKey}>{i18n.t('transactions.withdraw_confirm_amount')}</Text>
            <Text style={[styles.summaryValue, styles.summaryAmount]}>
              {formatXAF(xaf * 100)}
            </Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryKey}>{i18n.t('transactions.withdraw_confirm_channel')}</Text>
            <Text style={styles.summaryValue}>
              {i18n.t(CHANNEL_LABEL_KEY[selectedChannel])}
            </Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryKey}>{i18n.t('transactions.withdraw_confirm_phone')}</Text>
            <Text style={[styles.summaryValue, styles.monoText]}>{phone.trim()}</Text>
          </View>
        </View>

        {/* PIN keypad */}
        <Text style={styles.pinTitle}>{i18n.t('transactions.withdraw_pin_title')}</Text>
        <Text style={styles.pinSubtitle}>{i18n.t('transactions.withdraw_pin_subtitle')}</Text>

        {pinError ? <Text style={styles.errorText}>{pinError}</Text> : null}

        <PINKeypad
          onKeyPress={(key) => {
            if (key === 'backspace') setPin((p) => p.slice(0, -1));
            else if (pin.length < 6) setPin((p) => p + key);
          }}
          disabled={pinVerifying || isPending}
        />

        <TerahButton
          label={
            pinVerifying || isPending
              ? i18n.t('common.loading')
              : i18n.t('transactions.withdraw_submit')
          }
          onPress={handleSubmit}
          loading={pinVerifying || isPending}
          disabled={pin.length < 4 || pinVerifying || isPending}
          style={styles.cta}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:   { flex: 1, backgroundColor: colors.offWhite },
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
  channelIcon: { marginRight: spacing.md },
  channelInfo: { flex: 1 },
  channelLabel: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: colors.navy,
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
    marginBottom: spacing.sm,
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
    flex: 1,
  },
  summaryValue: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.darkGrey,
    flex: 2,
    textAlign: 'right',
  },
  summaryAmount: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 18,
    color: colors.navy,
  },
  monoText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
  },
  pinTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 16,
    color: colors.navy,
    textAlign: 'center',
    marginTop: spacing.md,
    marginBottom: 4,
  },
  pinSubtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  cta: { marginTop: spacing.md },
});
