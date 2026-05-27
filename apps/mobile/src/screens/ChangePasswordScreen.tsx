import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { TerahIcon } from '@/components/TerahIcon';
import { TerahButton } from '@/components/TerahButton';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';
import { getAccessToken } from '@/stores/authStore';

type ChangePasswordNavProp = NativeStackNavigationProp<RootStackParamList, 'ChangePassword'>;

interface ChangePasswordScreenProps {
  navigation: ChangePasswordNavProp;
}

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

export default function ChangePasswordScreen({ navigation }: ChangePasswordScreenProps) {
  const [currentPassword, setCurrentPassword]   = useState('');
  const [newPassword, setNewPassword]             = useState('');
  const [confirmPassword, setConfirmPassword]     = useState('');
  const [showCurrent, setShowCurrent]             = useState(false);
  const [showNew, setShowNew]                     = useState(false);
  const [showConfirm, setShowConfirm]             = useState(false);
  const [isLoading, setIsLoading]                 = useState(false);

  const validate = (): string | null => {
    if (!currentPassword) return i18n.t('profile.current_password');
    if (newPassword.length < 8) return i18n.t('profile.password_too_short');
    if (newPassword !== confirmPassword) return i18n.t('profile.password_mismatch');
    return null;
  };

  const handleSubmit = async () => {
    const error = validate();
    if (error) {
      Alert.alert(i18n.t('common.error'), error);
      return;
    }

    setIsLoading(true);
    try {
      const token = await getAccessToken();
      const res = await fetch(`${BASE_URL}/api/v1/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.message ?? i18n.t('common.generic_error'));
      }
      Alert.alert(i18n.t('common.success'), i18n.t('profile.password_changed'), [
        { text: i18n.t('common.confirm'), onPress: () => navigation.goBack() },
      ]);
    } catch (err: any) {
      Alert.alert(i18n.t('common.error'), err?.message ?? i18n.t('common.generic_error'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView style={styles.screen} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">

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

          <Text style={styles.title}>{i18n.t('profile.change_password_title')}</Text>

          {/* Current password */}
          <Text style={styles.fieldLabel}>{i18n.t('profile.current_password')}</Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder={i18n.t('profile.current_password_placeholder')}
              placeholderTextColor={colors.midGrey}
              secureTextEntry={!showCurrent}
              value={currentPassword}
              onChangeText={setCurrentPassword}
              autoCapitalize="none"
              returnKeyType="next"
            />
            <TouchableOpacity onPress={() => setShowCurrent((v) => !v)} style={styles.eyeButton} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <TerahIcon name={showCurrent ? 'eye-off-outline' : 'eye-outline'} size={20} color={colors.midGrey} />
            </TouchableOpacity>
          </View>

          {/* New password */}
          <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{i18n.t('profile.new_password')}</Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder={i18n.t('profile.new_password_placeholder')}
              placeholderTextColor={colors.midGrey}
              secureTextEntry={!showNew}
              value={newPassword}
              onChangeText={setNewPassword}
              autoCapitalize="none"
              returnKeyType="next"
            />
            <TouchableOpacity onPress={() => setShowNew((v) => !v)} style={styles.eyeButton} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <TerahIcon name={showNew ? 'eye-off-outline' : 'eye-outline'} size={20} color={colors.midGrey} />
            </TouchableOpacity>
          </View>

          {/* Confirm password */}
          <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{i18n.t('profile.confirm_password')}</Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder={i18n.t('profile.confirm_password_placeholder')}
              placeholderTextColor={colors.midGrey}
              secureTextEntry={!showConfirm}
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              autoCapitalize="none"
              returnKeyType="done"
              onSubmitEditing={handleSubmit}
            />
            <TouchableOpacity onPress={() => setShowConfirm((v) => !v)} style={styles.eyeButton} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <TerahIcon name={showConfirm ? 'eye-off-outline' : 'eye-outline'} size={20} color={colors.midGrey} />
            </TouchableOpacity>
          </View>

          {/* Match indicator */}
          {newPassword.length > 0 && confirmPassword.length > 0 && (
            <View style={styles.matchRow}>
              <TerahIcon
                name={newPassword === confirmPassword ? 'checkmark-circle' : 'close-circle'}
                size={16}
                color={newPassword === confirmPassword ? colors.success : colors.error}
              />
              <Text style={[styles.matchText, { color: newPassword === confirmPassword ? colors.success : colors.error }]}>
                {newPassword === confirmPassword ? i18n.t('common.confirm') : i18n.t('profile.password_mismatch')}
              </Text>
            </View>
          )}

          <TerahButton
            label={isLoading ? i18n.t('common.loading') : i18n.t('profile.change_password_submit')}
            onPress={handleSubmit}
            loading={isLoading}
            disabled={isLoading || !currentPassword || !newPassword || !confirmPassword}
            style={styles.cta}
          />
        </ScrollView>
      </KeyboardAvoidingView>
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
    marginBottom: 28,
  },
  fieldLabel: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.darkGrey,
    marginBottom: 6,
  },
  fieldLabelSpaced: {
    marginTop: 16,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.lightGrey,
    paddingHorizontal: 14,
    height: 52,
  },
  input: {
    flex: 1,
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.darkGrey,
    paddingVertical: 0,
  },
  eyeButton: {
    padding: 4,
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  matchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
  },
  matchText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
  },
  cta: {
    marginTop: 32,
  },
});
