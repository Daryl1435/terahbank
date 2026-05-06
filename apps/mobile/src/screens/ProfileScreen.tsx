/**
 * FR-050: Profile access — view and update personal info, security settings.
 * Milestone 2.4 delivers the shell with navigation. Full edit functionality
 * is Milestone 5 (User Settings module).
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
import { TerahButton } from '@/components/TerahButton';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

type ProfileNavProp = NativeStackNavigationProp<RootStackParamList, 'Profile'>;

interface ProfileScreenProps {
  navigation: ProfileNavProp;
}

interface ProfileRowProps {
  label: string;
  value?: string;
  onPress?: () => void;
  chevron?: boolean;
}

const ProfileRow: React.FC<ProfileRowProps> = ({ label, value, onPress, chevron = false }) => (
  <TouchableOpacity
    onPress={onPress}
    disabled={!onPress}
    activeOpacity={onPress ? 0.7 : 1}
    accessibilityRole={onPress ? 'button' : 'none'}
    style={styles.row}
  >
    <Text style={styles.rowLabel}>{label}</Text>
    <View style={styles.rowRight}>
      {value ? <Text style={styles.rowValue}>{value}</Text> : null}
      {chevron ? <Text style={styles.chevron}>›</Text> : null}
    </View>
  </TouchableOpacity>
);

export default function ProfileScreen({ navigation }: ProfileScreenProps) {
  const kycStatus = useAuthStore((s) => s.kycStatus);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const kycLabel =
    kycStatus === 'approved'
      ? i18n.t('profile.kyc_approved')
      : kycStatus === 'rejected'
      ? i18n.t('profile.kyc_rejected')
      : i18n.t('profile.kyc_pending');

  const kycColor =
    kycStatus === 'approved' ? colors.success
    : kycStatus === 'rejected' ? colors.error
    : colors.warning;

  const handleLogout = () => {
    Alert.alert(
      i18n.t('profile.logout'),
      'Êtes-vous sûr de vouloir vous déconnecter ?',
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

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.offWhite }} edges={['top', 'bottom']}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
      {/* Back */}
      <TouchableOpacity
        onPress={() => navigation.goBack()}
        style={styles.backButton}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('common.back')}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Text style={styles.backText}>← {i18n.t('common.back')}</Text>
      </TouchableOpacity>

      {/* Avatar */}
      <View style={styles.avatarSection}>
        <View style={styles.avatar}>
          <Text style={styles.avatarLetter}>U</Text>
        </View>
        <Text style={styles.screenTitle}>{i18n.t('profile.title')}</Text>
      </View>

      {/* Account status */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{i18n.t('profile.account_status')}</Text>
        <View style={styles.card}>
          <ProfileRow label={i18n.t('profile.kyc_status')} />
          <View style={styles.kycBadgeRow}>
            <View style={[styles.kycBadge, { backgroundColor: kycColor + '20' }]}>
              <Text style={[styles.kycBadgeText, { color: kycColor }]}>
                {kycLabel}
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* Personal info — edit stubs (Milestone 5) */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{i18n.t('profile.personal_info')}</Text>
        <View style={styles.card}>
          <ProfileRow
            label="Nom complet"
            value="—"
            onPress={() =>
              Alert.alert('Bientôt disponible', 'La modification du profil sera disponible au Jalon 5.')
            }
            chevron
          />
          <ProfileRow
            label="Téléphone"
            value="—"
            onPress={() =>
              Alert.alert('Bientôt disponible', 'La modification du profil sera disponible au Jalon 5.')
            }
            chevron
          />
          <ProfileRow
            label="Email"
            value="—"
            onPress={() =>
              Alert.alert('Bientôt disponible', 'La modification du profil sera disponible au Jalon 5.')
            }
            chevron
          />
        </View>
      </View>

      {/* Security */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{i18n.t('profile.security')}</Text>
        <View style={styles.card}>
          <ProfileRow
            label={i18n.t('profile.change_password')}
            onPress={() =>
              Alert.alert('Bientôt disponible', 'Le changement de mot de passe sera disponible au Jalon 5.')
            }
            chevron
          />
          <ProfileRow
            label={i18n.t('profile.biometric_settings')}
            onPress={() =>
              Alert.alert('Bientôt disponible', 'Les paramètres biométriques seront disponibles au Jalon 5.')
            }
            chevron
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

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    paddingHorizontal: 16,
    paddingBottom: 48,
  },
  backButton: {
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
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
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
    fontSize: 13,
    color: colors.midGrey,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
    minHeight: 52,
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
    gap: 8,
  },
  rowValue: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
  },
  chevron: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 20,
    color: colors.midGrey,
  },
  kycBadgeRow: {
    paddingHorizontal: 16,
    paddingVertical: 10,
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
  logoutButton: {
    marginTop: 8,
  },
  logoutText: {
    color: colors.error,
  },
});
