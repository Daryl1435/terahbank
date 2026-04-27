/**
 * Account type picker — entry point for opening any account.
 * Shows 3 cards: Standard, Project, Term Deposit.
 * User taps one → navigates to the specific creation form.
 */
import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

type OpenAccountNavProp = NativeStackNavigationProp<RootStackParamList, 'OpenAccount'>;

interface OpenAccountScreenProps {
  navigation: OpenAccountNavProp;
}

interface AccountTypeCard {
  typeKey: string;
  descKey: string;
  icon: string;
  screen: keyof RootStackParamList;
  color: string;
}

const ACCOUNT_TYPES: AccountTypeCard[] = [
  {
    typeKey: 'accounts.standard',
    descKey: 'accounts.standard_desc',
    icon: '💰',
    screen: 'OpenStandardAccount',
    color: colors.teal,
  },
  {
    typeKey: 'accounts.project',
    descKey: 'accounts.project_desc',
    icon: '🎯',
    screen: 'OpenProjectAccount',
    color: '#7C3AED',  // purple accent for project
  },
  {
    typeKey: 'accounts.term_deposit',
    descKey: 'accounts.term_deposit_desc',
    icon: '📈',
    screen: 'OpenTermDeposit',
    color: colors.navy,
  },
];

export default function OpenAccountScreen({ navigation }: OpenAccountScreenProps) {
  return (
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

      <Text style={styles.title}>{i18n.t('accounts.choose_type')}</Text>
      <Text style={styles.subtitle}>{i18n.t('accounts.choose_type_subtitle')}</Text>

      <View style={styles.cards}>
        {ACCOUNT_TYPES.map((item) => (
          <TouchableOpacity
            key={item.screen}
            onPress={() => navigation.navigate(item.screen as any)}
            activeOpacity={0.85}
            accessibilityRole="button"
            accessibilityLabel={i18n.t(item.typeKey)}
            style={styles.card}
          >
            <View style={[styles.iconContainer, { backgroundColor: item.color + '15' }]}>
              <Text style={styles.icon}>{item.icon}</Text>
            </View>
            <View style={styles.cardText}>
              <Text style={[styles.cardTitle, { color: item.color }]}>
                {i18n.t(item.typeKey)}
              </Text>
              <Text style={styles.cardDesc}>{i18n.t(item.descKey)}</Text>
            </View>
            <Text style={[styles.chevron, { color: item.color }]}>›</Text>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    paddingHorizontal: 16,
    paddingBottom: 40,
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
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 8,
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.midGrey,
    marginBottom: 28,
    lineHeight: 22,
  },
  cards: {
    gap: 12,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 18,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  iconContainer: {
    width: 52,
    height: 52,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  icon: {
    fontSize: 26,
  },
  cardText: {
    flex: 1,
  },
  cardTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    marginBottom: 4,
  },
  cardDesc: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    lineHeight: 18,
  },
  chevron: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
  },
});
