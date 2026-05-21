/**
 * FR-050: Profile — personal info, security settings, language preference.
 */
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
import type { RootStackParamList } from '../../App';
import { useAuthStore } from '@/stores/authStore';
import { useAppStore } from '@/stores/appStore';
import type { FontSize } from '@/stores/appStore';
import { TerahButton } from '@/components/TerahButton';
import { TerahIcon } from '@/components/TerahIcon';
import type { TerahIconName } from '@/components/TerahIcon';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

type ProfileNavProp = NativeStackNavigationProp<RootStackParamList, 'Profile'>;

interface ProfileScreenProps {
  navigation: ProfileNavProp;
}

// ── Generic settings row ───────────────────────────────────────────────────────

interface ProfileRowProps {
  icon?:    TerahIconName;
  label:    string;
  value?:   string;
  onPress?: () => void;
  chevron?: boolean;
  last?:    boolean;
}

const ProfileRow: React.FC<ProfileRowProps> = ({ icon, label, value, onPress, chevron = false, last = false }) => (
  <TouchableOpacity
    onPress={onPress}
    disabled={!onPress}
    activeOpacity={onPress ? 0.7 : 1}
    accessibilityRole={onPress ? 'button' : 'none'}
    style={[styles.row, last && styles.rowLast]}
  >
    {icon && (
      <View style={styles.rowIcon}>
        <TerahIcon name={icon} size={18} color={colors.teal} />
      </View>
    )}
    <Text style={styles.rowLabel}>{label}</Text>
    <View style={styles.rowRight}>
      {value ? <Text style={styles.rowValue}>{value}</Text> : null}
      {chevron ? <TerahIcon name="chevron-forward" size={18} color={colors.midGrey} /> : null}
    </View>
  </TouchableOpacity>
);

// ── Main screen ───────────────────────────────────────────────────────────────

export default function ProfileScreen({ navigation }: ProfileScreenProps) {
  const kycStatus   = useAuthStore((s) => s.kycStatus);
  const clearAuth   = useAuthStore((s) => s.clearAuth);
  const language    = useAppStore((s) => s.language);
  const setLanguage = useAppStore((s) => s.setLanguage);
  const fontSize    = useAppStore((s) => s.fontSize);
  const setFontSize = useAppStore((s) => s.setFontSize);

  const kycLabel =
    kycStatus === 'approved' ? i18n.t('profile.kyc_approved')
    : kycStatus === 'rejected' ? i18n.t('profile.kyc_rejected')
    : i18n.t('profile.kyc_pending');

  const kycColor =
    kycStatus === 'approved' ? colors.success
    : kycStatus === 'rejected' ? colors.error
    : colors.warning;

  const handleLogout = () => {
    Alert.alert(
      i18n.t('profile.logout'),
      i18n.t('profile.logout_confirm'),
      [
        { text: i18n.t('common.cancel'), style: 'cancel' },
        {
          text: i18n.t('profile.logout'),
          style: 'destructive',
          onPress: () => {
            clearAuth();
            navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
          },
        },
      ],
    );
  };

  // Switch language — NavigationContainer re-mounts via key in App.tsx
  const handleLanguageChange = (lang: 'fr' | 'en') => {
    if (lang === language) return;
    i18n.locale = lang;
    setLanguage(lang);
    // App.tsx keys NavigationContainer on `language` → whole app re-mounts
    // with the new locale, user lands back on Dashboard in the new language
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.container}>

        {/* Back button */}
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <TerahIcon name="chevron-back" size={20} color={colors.teal} />
          <Text style={styles.backText}>{i18n.t('common.back')}</Text>
        </TouchableOpacity>

        {/* ── Avatar ─────────────────────────────────────────────────────── */}
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarLetter}>U</Text>
          </View>
          <Text style={styles.screenTitle}>{i18n.t('profile.title')}</Text>
        </View>

        {/* ── Account status ──────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('profile.account_status')}</Text>
          <View style={styles.card}>
            <ProfileRow
              icon="shield-checkmark-outline"
              label={i18n.t('profile.kyc_status')}
              last
            />
            <View style={styles.kycBadgeRow}>
              <View style={[styles.kycBadge, { backgroundColor: kycColor + '20' }]}>
                <Text style={[styles.kycBadgeText, { color: kycColor }]}>{kycLabel}</Text>
              </View>
            </View>
          </View>
        </View>

        {/* ── Personal info ────────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('profile.personal_info')}</Text>
          <View style={styles.card}>
            <ProfileRow
              icon="person-outline"
              label={i18n.t('profile.full_name')}
              value="—"
              onPress={() => Alert.alert('Bientôt disponible', 'Jalon 5.')}
              chevron
            />
            <ProfileRow
              icon="call-outline"
              label={i18n.t('auth.phone_label')}
              value="—"
              onPress={() => Alert.alert('Bientôt disponible', 'Jalon 5.')}
              chevron
            />
            <ProfileRow
              icon="mail-outline"
              label={i18n.t('auth.email_label')}
              value="—"
              onPress={() => Alert.alert('Bientôt disponible', 'Jalon 5.')}
              chevron
              last
            />
          </View>
        </View>

        {/* ── Language ─────────────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('language.section_title')}</Text>
          <View style={styles.card}>
            <View style={styles.langRow}>
              {/* French option */}
              <TouchableOpacity
                style={[styles.langCard, language === 'fr' && styles.langCardActive]}
                onPress={() => handleLanguageChange('fr')}
                accessibilityRole="radio"
                accessibilityState={{ selected: language === 'fr' }}
              >
                <Text style={styles.langFlag}>🇫🇷</Text>
                <Text style={[styles.langLabel, language === 'fr' && styles.langLabelActive]}>
                  {i18n.t('language.french')}
                </Text>
                {language === 'fr' && (
                  <TerahIcon name="checkmark-circle" size={16} color={colors.teal} />
                )}
              </TouchableOpacity>

              {/* English option */}
              <TouchableOpacity
                style={[styles.langCard, language === 'en' && styles.langCardActive]}
                onPress={() => handleLanguageChange('en')}
                accessibilityRole="radio"
                accessibilityState={{ selected: language === 'en' }}
              >
                <Text style={styles.langFlag}>🇬🇧</Text>
                <Text style={[styles.langLabel, language === 'en' && styles.langLabelActive]}>
                  {i18n.t('language.english')}
                </Text>
                {language === 'en' && (
                  <TerahIcon name="checkmark-circle" size={16} color={colors.teal} />
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* ── Font size ─────────────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('profile.font_size')}</Text>
          <View style={styles.card}>
            <View style={styles.fontSizeRow}>
              {(['small', 'medium', 'large'] as const).map((size) => (
                <TouchableOpacity
                  key={size}
                  style={[styles.fontSizeCard, fontSize === size && styles.fontSizeCardActive]}
                  onPress={() => setFontSize(size)}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: fontSize === size }}
                >
                  <Text style={[styles.fontSizeLabel, fontSize === size && styles.fontSizeLabelActive]}>
                    {i18n.t(`profile.font_size_${size}`)}
                  </Text>
                  <Text style={[
                    styles.fontSizePreview,
                    fontSize === size && styles.fontSizeLabelActive,
                    { fontSize: size === 'small' ? 14 : size === 'medium' ? 18 : 24 },
                  ]}>
                    Aa
                  </Text>
                  {fontSize === size && (
                    <TerahIcon name="checkmark-circle" size={14} color={colors.teal} />
                  )}
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>

        {/* ── Security ─────────────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t('profile.security')}</Text>
          <View style={styles.card}>
            <ProfileRow
              icon="key-outline"
              label={i18n.t('profile.change_password')}
              onPress={() => Alert.alert('Bientôt disponible', 'Jalon 5.')}
              chevron
            />
            <ProfileRow
              icon="finger-print-outline"
              label={i18n.t('profile.biometric_settings')}
              onPress={() => Alert.alert('Bientôt disponible', 'Jalon 5.')}
              chevron
              last
            />
          </View>
        </View>

        {/* Logout */}
        <TerahButton
          label={i18n.t('profile.logout')}
          onPress={handleLogout}
          variant="ghost"
          style={styles.logoutButton}
          textStyle={styles.logoutText}
        />

      </ScrollView>
    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  screen: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    paddingHorizontal: 16,
    paddingBottom: 48,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingTop: 24,
    paddingBottom: 16,
    minHeight: 44,
    alignSelf: 'flex-start',
  },
  backText: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.teal,
  },
  avatarSection: {
    alignItems: 'center',
    marginBottom: 28,
  },
  avatar: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    shadowColor: colors.teal,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  avatarLetter: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 32,
    color: '#FFFFFF',
  },
  screenTitle: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 22,
    color: colors.navy,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 11,
    color: colors.midGrey,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 8,
    paddingLeft: 4,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.lightGrey,
    minHeight: 52,
  },
  rowLast: {
    borderBottomWidth: 0,
  },
  rowIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: `${colors.teal}15`,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  rowLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.darkGrey,
    flex: 1,
  },
  rowRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  rowValue: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
  },
  kycBadgeRow: {
    paddingHorizontal: 16,
    paddingBottom: 14,
  },
  kycBadge: {
    alignSelf: 'flex-start',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  kycBadgeText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
  },

  // Language selector inside card
  langRow: {
    flexDirection: 'row',
    padding: 12,
    gap: 10,
  },
  langCard: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.lightGrey,
    backgroundColor: colors.offWhite,
  },
  langCardActive: {
    borderColor: colors.teal,
    backgroundColor: `${colors.teal}10`,
  },
  langFlag: {
    fontSize: 20,
  },
  langLabel: {
    flex: 1,
    fontFamily: 'Poppins_500Medium',
    fontSize: 13,
    color: colors.midGrey,
  },
  langLabelActive: {
    color: colors.navy,
  },

  // Font size selector
  fontSizeRow: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
  },
  fontSizeCard: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.lightGrey,
    backgroundColor: colors.offWhite,
  },
  fontSizeCardActive: {
    borderColor: colors.teal,
    backgroundColor: `${colors.teal}10`,
  },
  fontSizeLabel: {
    fontFamily: 'Poppins_500Medium',
    fontSize: 11,
    color: colors.midGrey,
  },
  fontSizeLabelActive: {
    color: colors.navy,
  },
  fontSizePreview: {
    fontFamily: 'Poppins_700Bold',
    color: colors.midGrey,
  },

  logoutButton: {
    marginTop: 8,
  },
  logoutText: {
    color: colors.error,
  },
});
