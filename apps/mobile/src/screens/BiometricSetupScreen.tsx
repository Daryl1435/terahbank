/**
 * BiometricSetupScreen — FR-006: Optional biometric authentication setup.
 * Uses expo-local-authentication. Checks hardware + enrollment before offering.
 * Enable → biometric prompt → save preference → KYCUpload.
 * Skip → KYCUpload directly.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { TerahButton } from '@/components/TerahButton';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface BiometricSetupScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'BiometricSetup'>;
}

type BiometricAvailability = 'checking' | 'available' | 'no_hardware' | 'not_enrolled';

export function BiometricSetupScreen({ navigation }: BiometricSetupScreenProps) {
  const [availability, setAvailability] = useState<BiometricAvailability>('checking');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const hasHardware = await LocalAuthentication.hasHardwareAsync();
        if (!hasHardware) { setAvailability('no_hardware'); return; }
        const isEnrolled = await LocalAuthentication.isEnrolledAsync();
        setAvailability(isEnrolled ? 'available' : 'not_enrolled');
      } catch {
        // expo-local-authentication not supported on this platform (e.g. web)
        setAvailability('no_hardware');
      }
    })();
  }, []);

  const handleEnable = async () => {
    setLoading(true);
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: i18n.t('auth.biometric_title'),
        cancelLabel: i18n.t('common.cancel'),
        disableDeviceFallback: true,
      });
      if (result.success) {
        await SecureStore.setItemAsync('biometric_enabled', '1');
      }
    } catch {
      // Biometric not available on this platform — skip silently
    } finally {
      setLoading(false);
      navigation.navigate('KYCUpload');
    }
  };

  const handleSkip = () => navigation.navigate('KYCUpload');

  const unavailableMessage =
    availability === 'no_hardware'
      ? i18n.t('auth.biometric_not_available')
      : availability === 'not_enrolled'
      ? i18n.t('auth.biometric_enrolled_error')
      : null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.offWhite }} edges={['top', 'bottom']}>
      <View style={styles.container}>
      {/* Icon placeholder — Phosphor icon would go here */}
      <View style={styles.iconCircle}>
        <Text style={styles.iconText}>🔒</Text>
      </View>

      <Text style={styles.title}>{i18n.t('auth.biometric_title')}</Text>
      <Text style={styles.subtitle}>{i18n.t('auth.biometric_subtitle')}</Text>

      {unavailableMessage ? (
        <Text style={styles.unavailableText} accessibilityRole="alert">
          {unavailableMessage}
        </Text>
      ) : null}

      {availability === 'available' ? (
        <TerahButton
          label={i18n.t('auth.biometric_enable')}
          onPress={handleEnable}
          loading={loading}
          style={styles.enableButton}
        />
      ) : null}

      <TerahButton
        label={i18n.t('auth.biometric_skip')}
        onPress={handleSkip}
        variant="ghost"
        disabled={loading}
      />
      </View>
    </SafeAreaView>
  );
}

export default BiometricSetupScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.offWhite,
    paddingHorizontal: 24,
    paddingTop: 64,
    alignItems: 'center',
  },
  iconCircle: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.navy,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 32,
  },
  iconText: {
    fontSize: 40,
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
    marginBottom: 40,
    textAlign: 'center',
  },
  unavailableText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.warning,
    textAlign: 'center',
    marginBottom: 24,
    paddingHorizontal: 8,
    lineHeight: 22,
  },
  enableButton: {
    width: '100%',
    marginBottom: 12,
  },
});
