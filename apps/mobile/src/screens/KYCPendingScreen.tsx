/**
 * KYCPendingScreen — shown after KYC document submission.
 * Informs user that review takes 24–48 business hours.
 * During registration flow: "Got it" → Login.
 * During post-login flow (authenticated, pending): App.tsx handles gate; button resets to Login.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { TerahButton } from '@/components/TerahButton';
import { useAuthStore } from '@/stores/authStore';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface KYCPendingScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'KYCPending'>;
}

export function KYCPendingScreen({ navigation }: KYCPendingScreenProps) {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const handleDone = async () => {
    if (isAuthenticated) {
      // Authenticated but pending — clear auth so user goes back to Login
      await clearAuth();
    } else {
      navigation.navigate('Login');
    }
  };

  return (
    <View style={styles.container}>
      {/* Success icon */}
      <View style={styles.iconCircle}>
        <Text style={styles.iconText}>✓</Text>
      </View>

      <Text style={styles.title}>{i18n.t('auth.kyc_pending_title')}</Text>
      <Text style={styles.subtitle}>{i18n.t('auth.kyc_pending_subtitle')}</Text>
      <Text style={styles.note}>{i18n.t('auth.kyc_pending_note')}</Text>

      <TerahButton
        label={i18n.t('auth.kyc_pending_button')}
        onPress={handleDone}
        style={styles.button}
      />
    </View>
  );
}

export default KYCPendingScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.offWhite,
    paddingHorizontal: 32,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 48,
  },
  iconCircle: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.success,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 32,
  },
  iconText: {
    fontSize: 44,
    color: '#FFFFFF',
    fontFamily: 'Poppins_700Bold',
    lineHeight: 56,
  },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 12,
    textAlign: 'center',
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.darkGrey,
    lineHeight: 24,
    textAlign: 'center',
    marginBottom: 16,
  },
  note: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    lineHeight: 22,
    textAlign: 'center',
    marginBottom: 48,
  },
  button: {
    width: '100%',
  },
});
