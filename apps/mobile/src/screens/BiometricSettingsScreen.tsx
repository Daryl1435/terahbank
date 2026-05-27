import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Switch,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { TerahIcon } from '@/components/TerahIcon';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

type BiometricSettingsNavProp = NativeStackNavigationProp<RootStackParamList, 'BiometricSettings'>;

interface BiometricSettingsScreenProps {
  navigation: BiometricSettingsNavProp;
}

const BIOMETRIC_ENABLED_KEY = 'biometric_enabled';

type HardwareState = 'checking' | 'available' | 'no_hardware' | 'not_enrolled';

export default function BiometricSettingsScreen({ navigation }: BiometricSettingsScreenProps) {
  const [hardwareState, setHardwareState] = useState<HardwareState>('checking');
  const [isEnabled, setIsEnabled]         = useState(false);
  const [isToggling, setIsToggling]       = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const hasHardware = await LocalAuthentication.hasHardwareAsync();
        if (!hasHardware) { setHardwareState('no_hardware'); return; }
        const isEnrolled = await LocalAuthentication.isEnrolledAsync();
        if (!isEnrolled) { setHardwareState('not_enrolled'); return; }
        setHardwareState('available');

        const stored = await SecureStore.getItemAsync(BIOMETRIC_ENABLED_KEY);
        setIsEnabled(stored === 'true');
      } catch {
        setHardwareState('no_hardware');
      }
    })();
  }, []);

  const handleToggle = async (value: boolean) => {
    if (hardwareState !== 'available') return;
    setIsToggling(true);
    try {
      if (value) {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage: i18n.t('profile.biometric_prompt'),
          cancelLabel: i18n.t('common.cancel'),
          disableDeviceFallback: true,
        });
        if (!result.success) {
          setIsToggling(false);
          return;
        }
      }
      await SecureStore.setItemAsync(BIOMETRIC_ENABLED_KEY, String(value));
      setIsEnabled(value);
      Alert.alert(
        i18n.t('common.success'),
        value ? i18n.t('profile.biometric_enabled') : i18n.t('profile.biometric_disabled'),
      );
    } catch {
      Alert.alert(i18n.t('common.error'), i18n.t('common.generic_error'));
    } finally {
      setIsToggling(false);
    }
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

        <Text style={styles.title}>{i18n.t('profile.biometric_title')}</Text>

        {/* Main toggle card */}
        <View style={styles.card}>
          <View style={styles.iconWrap}>
            <TerahIcon name="finger-print-outline" size={28} color={colors.teal} />
          </View>
          <View style={styles.cardContent}>
            <Text style={styles.cardLabel}>{i18n.t('profile.biometric_enable_label')}</Text>
            <Text style={styles.cardDesc}>{i18n.t('profile.biometric_enable_desc')}</Text>
          </View>
          <Switch
            value={isEnabled}
            onValueChange={handleToggle}
            trackColor={{ false: colors.lightGrey, true: colors.teal }}
            thumbColor="#fff"
            disabled={hardwareState !== 'available' || isToggling}
          />
        </View>

        {/* Unavailability notices */}
        {hardwareState === 'no_hardware' && (
          <View style={styles.noticeBanner}>
            <TerahIcon name="warning-outline" size={18} color={colors.warning} />
            <Text style={styles.noticeText}>{i18n.t('profile.biometric_not_available')}</Text>
          </View>
        )}
        {hardwareState === 'not_enrolled' && (
          <View style={styles.noticeBanner}>
            <TerahIcon name="information-circle-outline" size={18} color={colors.info} />
            <Text style={styles.noticeText}>{i18n.t('profile.biometric_not_enrolled')}</Text>
          </View>
        )}

        {/* Status indicator */}
        {hardwareState === 'available' && (
          <View style={[styles.statusRow, { backgroundColor: isEnabled ? `${colors.success}15` : `${colors.lightGrey}80` }]}>
            <TerahIcon
              name={isEnabled ? 'checkmark-circle' : 'close-circle'}
              size={18}
              color={isEnabled ? colors.success : colors.midGrey}
            />
            <Text style={[styles.statusText, { color: isEnabled ? colors.success : colors.midGrey }]}>
              {isEnabled ? i18n.t('profile.biometric_enabled') : i18n.t('profile.biometric_disabled')}
            </Text>
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  screen: {
    flex: 1,
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
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 22,
    color: colors.navy,
    marginBottom: 24,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 14,
    padding: 16,
    gap: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
    marginBottom: 16,
  },
  iconWrap: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: `${colors.teal}15`,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  cardContent: {
    flex: 1,
  },
  cardLabel: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: colors.navy,
    marginBottom: 2,
  },
  cardDesc: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    lineHeight: 18,
  },
  noticeBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    backgroundColor: `${colors.warning}18`,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
  },
  noticeText: {
    flex: 1,
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.darkGrey,
    lineHeight: 18,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  statusText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
  },
});
