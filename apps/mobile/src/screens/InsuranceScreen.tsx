import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  RefreshControl,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';
import { useInsuranceProducts, useMyPolicies, useEnroll } from '@/hooks/useInsurance';
import type { InsuranceProduct } from '@/services/insurance';

type InsuranceNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Insurance'>;

interface InsuranceScreenProps {
  navigation: InsuranceNavigationProp;
}

const POLICY_TYPE_LABELS: Record<string, string> = {
  health: '🏥',
  device: '📱',
  micro:  '🛡',
};

export default function InsuranceScreen({ navigation }: InsuranceScreenProps) {
  const [activeTab, setActiveTab] = useState<'policies' | 'catalog'>('policies');

  const { data: products, isLoading: productsLoading, refetch: refetchProducts } = useInsuranceProducts();
  const { data: policies, isLoading: policiesLoading, refetch: refetchPolicies, isRefetching } = useMyPolicies();
  const enroll = useEnroll();

  const activePolicies = policies?.filter((p) => p.status === 'active') ?? [];
  const hasActivePolicies = activePolicies.length > 0;

  function handleEnroll(product: InsuranceProduct) {
    Alert.alert(
      i18n.t('insurance.enroll_title'),
      i18n.t('insurance.enroll_confirm', {
        name: product.name,
        premium: formatXAF(product.monthly_premium_xaf),
      }),
      [
        { text: i18n.t('common.cancel'), style: 'cancel' },
        {
          text: i18n.t('insurance.enroll_button'),
          onPress: async () => {
            try {
              const result = await enroll.mutateAsync(product.product_id);
              // Open partner redirect URL
              if (result.redirect_url) {
                await Linking.openURL(result.redirect_url);
              }
            } catch (err: any) {
              Alert.alert(i18n.t('common.error'), err.message ?? i18n.t('common.generic_error'));
            }
          },
        },
      ],
    );
  }

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
        <Text style={styles.appBarTitle}>{i18n.t('insurance.title')}</Text>
        <View style={{ width: 32 }} />
      </View>

      {/* Tab switcher */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'policies' && styles.tabActive]}
          onPress={() => setActiveTab('policies')}
          accessibilityRole="tab"
        >
          <Text style={[styles.tabLabel, activeTab === 'policies' && styles.tabLabelActive]}>
            {i18n.t('insurance.tab_policies')}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'catalog' && styles.tabActive]}
          onPress={() => setActiveTab('catalog')}
          accessibilityRole="tab"
        >
          <Text style={[styles.tabLabel, activeTab === 'catalog' && styles.tabLabelActive]}>
            {i18n.t('insurance.tab_catalog')}
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={() => { refetchPolicies(); refetchProducts(); }}
            tintColor={colors.teal}
          />
        }
      >
        {/* ── My Policies tab ── */}
        {activeTab === 'policies' && (
          <>
            {policiesLoading ? (
              <View style={styles.loadingBox}>
                <Text style={styles.loadingText}>{i18n.t('common.loading')}</Text>
              </View>
            ) : !hasActivePolicies ? (
              <View style={styles.emptyState}>
                <Text style={styles.emptyIcon}>🛡</Text>
                <Text style={styles.emptyTitle}>{i18n.t('insurance.no_policies_title')}</Text>
                <Text style={styles.emptySubtext}>{i18n.t('insurance.no_policies_subtitle')}</Text>
                <TouchableOpacity
                  style={styles.catalogCTA}
                  onPress={() => setActiveTab('catalog')}
                  accessibilityRole="button"
                >
                  <Text style={styles.catalogCTAText}>{i18n.t('insurance.browse_catalog')}</Text>
                </TouchableOpacity>
              </View>
            ) : (
              activePolicies.map((policy) => (
                <TouchableOpacity
                  key={policy.policy_id}
                  style={styles.policyCard}
                  onPress={() =>
                    navigation.navigate('InsurancePolicyDetail', { policyId: policy.policy_id })
                  }
                  accessibilityRole="button"
                  activeOpacity={0.75}
                >
                  <View style={styles.policyCardHeader}>
                    <Text style={styles.policyTypeIcon}>
                      {POLICY_TYPE_LABELS[policy.policy_type] ?? '🛡'}
                    </Text>
                    <View style={styles.policyCardInfo}>
                      <Text style={styles.policyName} numberOfLines={1}>
                        {policy.product_name}
                      </Text>
                      <Text style={styles.policyNumber}>{policy.policy_number}</Text>
                    </View>
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

                  <View style={styles.policyCardFooter}>
                    <Text style={styles.premiumLabel}>{i18n.t('insurance.monthly_premium')}</Text>
                    <Text style={styles.premiumAmount}>
                      {formatXAF(policy.monthly_premium_xaf)}{i18n.t('common.per_month')}
                    </Text>
                    {policy.days_until_expiry !== null && (
                      <Text
                        style={[
                          styles.expiryLabel,
                          policy.days_until_expiry <= 7 && styles.expiryUrgent,
                          policy.days_until_expiry <= 30 && policy.days_until_expiry > 7 && styles.expiryWarning,
                        ]}
                      >
                        {i18n.t('insurance.expires_in', { days: policy.days_until_expiry })}
                      </Text>
                    )}
                  </View>

                  <Text style={styles.chevron}>›</Text>
                </TouchableOpacity>
              ))
            )}
          </>
        )}

        {/* ── Product Catalog tab ── */}
        {activeTab === 'catalog' && (
          <>
            <Text style={styles.catalogIntro}>{i18n.t('insurance.catalog_intro')}</Text>

            {productsLoading ? (
              <View style={styles.loadingBox}>
                <Text style={styles.loadingText}>{i18n.t('common.loading')}</Text>
              </View>
            ) : (
              products?.map((product) => (
                <View key={product.product_id} style={styles.productCard}>
                  <View style={styles.productCardHeader}>
                    <Text style={styles.productTypeIcon}>
                      {POLICY_TYPE_LABELS[product.policy_type] ?? '🛡'}
                    </Text>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.productName}>{product.name}</Text>
                      <Text style={styles.partnerLabel}>
                        {i18n.t('insurance.partner')}: {product.partner_id}
                      </Text>
                    </View>
                  </View>

                  <Text style={styles.productDescription}>{product.description}</Text>

                  <View style={styles.featureList}>
                    {product.features.map((f, idx) => (
                      <Text key={idx} style={styles.featureItem}>
                        ✓ {f}
                      </Text>
                    ))}
                  </View>

                  <View style={styles.productFooter}>
                    <View>
                      <Text style={styles.premiumLabel}>{i18n.t('insurance.monthly_premium')}</Text>
                      <Text style={styles.productPremium}>
                        {formatXAF(product.monthly_premium_xaf)}{i18n.t('common.per_month')}
                      </Text>
                    </View>
                    <View>
                      <Text style={styles.premiumLabel}>{i18n.t('insurance.max_coverage')}</Text>
                      <Text style={styles.productCoverage}>
                        {formatXAF(product.max_coverage_xaf)}
                      </Text>
                    </View>
                  </View>

                  <TouchableOpacity
                    style={[styles.enrollButton, enroll.isPending && styles.enrollButtonDisabled]}
                    onPress={() => handleEnroll(product)}
                    disabled={enroll.isPending}
                    accessibilityRole="button"
                  >
                    <Text style={styles.enrollButtonText}>
                      {enroll.isPending
                        ? i18n.t('common.loading')
                        : i18n.t('insurance.enroll_button')}
                    </Text>
                  </TouchableOpacity>
                </View>
              ))
            )}
          </>
        )}

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
    color: colors.white,
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.navy,
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: colors.teal,
  },
  tabLabel: {
    color: colors.midGrey,
    fontFamily: 'Poppins_500Medium',
    fontSize: 14,
  },
  tabLabelActive: {
    color: colors.teal,
  },
  scroll: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    padding: 16,
  },
  loadingBox: {
    padding: 32,
    alignItems: 'center',
  },
  loadingText: {
    color: colors.midGrey,
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 18,
    color: colors.navy,
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtext: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    textAlign: 'center',
    paddingHorizontal: 32,
    marginBottom: 24,
  },
  catalogCTA: {
    backgroundColor: colors.teal,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    minWidth: 44,
    minHeight: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  catalogCTAText: {
    color: colors.white,
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
  },
  // Policy card
  policyCard: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  policyCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  policyTypeIcon: {
    fontSize: 28,
    marginRight: 12,
  },
  policyCardInfo: {
    flex: 1,
  },
  policyName: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: colors.navy,
  },
  policyNumber: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    marginTop: 2,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusActive: {
    backgroundColor: colors.successBg,
  },
  statusCancelled: {
    backgroundColor: colors.errorBg,
  },
  statusText: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 12,
    color: colors.darkGrey,
  },
  policyCardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  premiumLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 11,
    color: colors.midGrey,
    marginBottom: 2,
  },
  premiumAmount: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.navy,
  },
  expiryLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    marginLeft: 'auto',
  },
  expiryWarning: {
    color: colors.warning,
  },
  expiryUrgent: {
    color: colors.error,
  },
  chevron: {
    position: 'absolute',
    right: 16,
    top: '50%',
    color: colors.midGrey,
    fontSize: 24,
  },
  // Product catalog
  catalogIntro: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    marginBottom: 16,
  },
  productCard: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  productCardHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 8,
  },
  productTypeIcon: {
    fontSize: 28,
  },
  productName: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: colors.navy,
    marginBottom: 2,
  },
  partnerLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
  },
  productDescription: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.darkGrey,
    marginBottom: 12,
    lineHeight: 20,
  },
  featureList: {
    marginBottom: 12,
    gap: 4,
  },
  featureItem: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.darkGrey,
  },
  productFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.offWhite,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  productPremium: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.teal,
  },
  productCoverage: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.navy,
    textAlign: 'right',
  },
  enrollButton: {
    backgroundColor: colors.teal,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  enrollButtonDisabled: {
    opacity: 0.5,
  },
  enrollButtonText: {
    color: colors.white,
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
  },
});
