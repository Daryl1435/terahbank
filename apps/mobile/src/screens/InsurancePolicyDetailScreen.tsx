import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';
import { useMyPolicies, useCancelPolicy } from '@/hooks/useInsurance';

type PolicyDetailNavigationProp = NativeStackNavigationProp<RootStackParamList, 'InsurancePolicyDetail'>;
type PolicyDetailRouteProp = RouteProp<RootStackParamList, 'InsurancePolicyDetail'>;

interface InsurancePolicyDetailScreenProps {
  navigation: PolicyDetailNavigationProp;
  route: PolicyDetailRouteProp;
}

const POLICY_TYPE_LABELS: Record<string, string> = {
  health: '🏥',
  device: '📱',
  micro:  '🛡',
};

const POLICY_TYPE_NAMES: Record<string, string> = {
  health: 'Santé',
  device: 'Appareil',
  micro:  'Micro-assurance',
};

export default function InsurancePolicyDetailScreen({
  navigation,
  route,
}: InsurancePolicyDetailScreenProps) {
  const { policyId } = route.params;

  const { data: policies, isLoading } = useMyPolicies();
  const cancelPolicy = useCancelPolicy();

  const policy = policies?.find((p) => p.policy_id === policyId);

  function handleCancel() {
    if (!policy) return;
    Alert.alert(
      i18n.t('insurance.cancel_title'),
      i18n.t('insurance.cancel_confirm', { name: policy.product_name }),
      [
        { text: i18n.t('common.back'), style: 'cancel' },
        {
          text: i18n.t('insurance.cancel_button'),
          style: 'destructive',
          onPress: async () => {
            try {
              await cancelPolicy.mutateAsync(policyId);
              navigation.goBack();
            } catch (err: any) {
              Alert.alert(i18n.t('common.error'), err.message ?? i18n.t('common.generic_error'));
            }
          },
        },
      ],
    );
  }

  if (isLoading || !policy) {
    return (
      <SafeAreaView style={styles.safe} edges={['top']}>
        <View style={styles.appBar}>
          <TouchableOpacity onPress={() => navigation.goBack()} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text style={styles.backIcon}>‹</Text>
          </TouchableOpacity>
          <Text style={styles.appBarTitle}>{i18n.t('insurance.policy_detail_title')}</Text>
          <View style={{ width: 32 }} />
        </View>
        <View style={styles.loadingBox}>
          <Text style={styles.loadingText}>{i18n.t('common.loading')}</Text>
        </View>
      </SafeAreaView>
    );
  }

  const daysLeft = policy.days_until_expiry;
  const isExpiringSoon = daysLeft !== null && daysLeft <= 30;
  const isExpiring7Days = daysLeft !== null && daysLeft <= 7;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* App bar */}
      <View style={styles.appBar}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
        >
          <Text style={styles.backIcon}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.appBarTitle}>{i18n.t('insurance.policy_detail_title')}</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
        {/* Hero card */}
        <View style={styles.heroCard}>
          <Text style={styles.heroIcon}>
            {POLICY_TYPE_LABELS[policy.policy_type] ?? '🛡'}
          </Text>
          <Text style={styles.heroName}>{policy.product_name}</Text>
          <Text style={styles.heroType}>
            {POLICY_TYPE_NAMES[policy.policy_type] ?? policy.policy_type}
          </Text>
          <View
            style={[
              styles.statusBadge,
              policy.status === 'active' ? styles.statusActive : styles.statusCancelled,
            ]}
          >
            <Text style={styles.statusText}>
              {i18n.t(`insurance.status_${policy.status}`)}
            </Text>
          </View>
        </View>

        {/* Expiry countdown banner */}
        {daysLeft !== null && isExpiringSoon && (
          <View style={[styles.expiryBanner, isExpiring7Days ? styles.expiryBannerUrgent : styles.expiryBannerWarning]}>
            <Text style={styles.expiryBannerText}>
              {isExpiring7Days
                ? i18n.t('insurance.expiry_urgent', { days: daysLeft })
                : i18n.t('insurance.expiry_warning', { days: daysLeft })}
            </Text>
          </View>
        )}

        {/* Details section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('insurance.details_section')}</Text>

          <DetailRow label={i18n.t('insurance.policy_number')} value={policy.policy_number} />
          <DetailRow label={i18n.t('insurance.partner')} value={policy.partner_id} />
          <DetailRow
            label={i18n.t('insurance.start_date')}
            value={new Date(policy.start_date).toLocaleDateString('fr-CM')}
          />
          <DetailRow
            label={i18n.t('insurance.expiry_date')}
            value={new Date(policy.expiry_date).toLocaleDateString('fr-CM')}
          />
          <DetailRow
            label={i18n.t('insurance.monthly_premium')}
            value={`${formatXAF(policy.monthly_premium_xaf)}/mois`}
          />
        </View>

        {/* Expiry countdown */}
        {daysLeft !== null && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{i18n.t('insurance.coverage_period')}</Text>
            <View style={styles.countdownRow}>
              <View style={styles.countdownBox}>
                <Text style={[styles.countdownNumber, isExpiring7Days && { color: colors.error }]}>
                  {daysLeft}
                </Text>
                <Text style={styles.countdownLabel}>{i18n.t('insurance.days_remaining')}</Text>
              </View>
            </View>
          </View>
        )}

        {/* Cancel action — only for active policies */}
        {policy.status === 'active' && (
          <TouchableOpacity
            style={[styles.cancelButton, cancelPolicy.isPending && styles.cancelButtonDisabled]}
            onPress={handleCancel}
            disabled={cancelPolicy.isPending}
            accessibilityRole="button"
          >
            <Text style={styles.cancelButtonText}>
              {cancelPolicy.isPending
                ? i18n.t('common.loading')
                : i18n.t('insurance.cancel_button')}
            </Text>
          </TouchableOpacity>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={detailStyles.row}>
      <Text style={detailStyles.label}>{label}</Text>
      <Text style={detailStyles.value}>{value}</Text>
    </View>
  );
}

const detailStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.lightGrey,
  },
  label: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    flex: 1,
  },
  value: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.navy,
    textAlign: 'right',
    flex: 1,
  },
});

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
    paddingVertical: 12,
    height: 56,
  },
  backIcon: {
    color: colors.teal,
    fontSize: 28,
    lineHeight: 32,
    fontFamily: 'Poppins_600SemiBold',
  },
  appBarTitle: {
    color: '#fff',
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
  },
  scroll: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    padding: 16,
  },
  loadingBox: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.offWhite,
  },
  loadingText: {
    color: colors.midGrey,
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
  },
  heroCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  heroIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  heroName: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 18,
    color: colors.navy,
    textAlign: 'center',
    marginBottom: 4,
  },
  heroType: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    marginBottom: 12,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusActive: {
    backgroundColor: '#E6FFF5',
  },
  statusCancelled: {
    backgroundColor: '#FFEAEA',
  },
  statusText: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.darkGrey,
  },
  expiryBanner: {
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
  },
  expiryBannerWarning: {
    backgroundColor: '#FFF8E1',
    borderLeftWidth: 4,
    borderLeftColor: colors.warning,
  },
  expiryBannerUrgent: {
    backgroundColor: '#FFEAEA',
    borderLeftWidth: 4,
    borderLeftColor: colors.error,
  },
  expiryBannerText: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.darkGrey,
  },
  section: {
    backgroundColor: '#fff',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 4,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 1,
  },
  sectionTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.navy,
    marginBottom: 4,
  },
  countdownRow: {
    flexDirection: 'row',
    paddingVertical: 16,
    justifyContent: 'center',
  },
  countdownBox: {
    alignItems: 'center',
  },
  countdownNumber: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 48,
    color: colors.teal,
    lineHeight: 56,
  },
  countdownLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
  },
  cancelButton: {
    borderWidth: 1.5,
    borderColor: colors.error,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
    minHeight: 44,
    justifyContent: 'center',
  },
  cancelButtonDisabled: {
    opacity: 0.5,
  },
  cancelButtonText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.error,
  },
});
