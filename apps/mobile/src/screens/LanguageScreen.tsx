/**
 * LanguageScreen — shown exactly once on first app launch, before Login.
 *
 * The user chooses French or English. The choice is saved to SecureStore
 * and applied to i18n immediately. This screen never appears again once
 * a language has been selected.
 *
 * Props:
 *   onComplete — called after the user confirms their choice.
 *                App.tsx hides this screen and shows the normal nav.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { TerahLogo } from '@/components/TerahLogo';
import { TerahButton } from '@/components/TerahButton';
import { TerahIcon } from '@/components/TerahIcon';
import { useAppStore } from '@/stores/appStore';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface LanguageScreenProps {
  onComplete: () => void;
}

type LangChoice = 'fr' | 'en';

export default function LanguageScreen({ onComplete }: LanguageScreenProps) {
  // Default to French — Cameroon is majority francophone
  const [selected, setSelected] = useState<LangChoice>('fr');

  const setLanguage         = useAppStore((s) => s.setLanguage);
  const setLanguageSelected = useAppStore((s) => s.setLanguageSelected);

  const handleContinue = () => {
    // 1. Update i18n locale immediately so the next screen renders correctly
    i18n.locale = selected;
    // 2. Persist choice to Zustand + SecureStore
    setLanguage(selected);
    // 3. Mark "has selected" so this screen is never shown again
    setLanguageSelected(true);
    // 4. Tell App.tsx to hide this screen and show the normal nav
    onComplete();
  };

  // Button label matches the chosen language (bilingual feel)
  const continueLabel = selected === 'fr' ? 'Continuer' : 'Continue';

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>

      {/* ── Brand area ─────────────────────────────────────────────────────── */}
      <View style={styles.brand}>
        {/* Shield symbol only — large, centered on navy */}
        <TerahLogo variant="symbol" width={80} onDark />

        <Text style={styles.appName}>TerahBank</Text>

        {/* Bilingual subtitle — shown before we know the user's preference */}
        <Text style={styles.titleFr}>Choisissez votre langue</Text>
        <Text style={styles.titleEn}>Choose your language</Text>
      </View>

      {/* ── Language cards ──────────────────────────────────────────────────── */}
      <View style={styles.cards}>
        <LanguageCard
          flagEmoji="🇫🇷"
          primaryLabel="Français"
          secondaryLabel="Langue officielle"
          selected={selected === 'fr'}
          onPress={() => setSelected('fr')}
        />
        <LanguageCard
          flagEmoji="🇬🇧"
          primaryLabel="English"
          secondaryLabel="Official language"
          selected={selected === 'en'}
          onPress={() => setSelected('en')}
        />
      </View>

      {/* ── Continue button ─────────────────────────────────────────────────── */}
      <View style={styles.footer}>
        <TerahButton label={continueLabel} onPress={handleContinue} />
      </View>

    </SafeAreaView>
  );
}

// ── Language option card ──────────────────────────────────────────────────────

interface LanguageCardProps {
  flagEmoji:     string;
  primaryLabel:  string;
  secondaryLabel: string;
  selected:      boolean;
  onPress:       () => void;
}

function LanguageCard({ flagEmoji, primaryLabel, secondaryLabel, selected, onPress }: LanguageCardProps) {
  return (
    <TouchableOpacity
      style={[styles.card, selected && styles.cardSelected]}
      onPress={onPress}
      activeOpacity={0.82}
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={`${primaryLabel} — ${secondaryLabel}`}
    >
      {/* Country flag */}
      <Text style={styles.flag}>{flagEmoji}</Text>

      {/* Language name + sub-label */}
      <View style={styles.cardText}>
        <Text style={[styles.cardPrimary, selected && styles.cardPrimarySelected]}>
          {primaryLabel}
        </Text>
        <Text style={styles.cardSecondary}>{secondaryLabel}</Text>
      </View>

      {/* Radio ring — filled teal dot when selected */}
      <View style={[styles.radio, selected && styles.radioSelected]}>
        {selected && <View style={styles.radioDot} />}
      </View>
    </TouchableOpacity>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.navy,
  },

  // Top brand / logo section
  brand: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingBottom: 8,
  },
  appName: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 30,
    color: colors.white,
    marginTop: 20,
    marginBottom: 28,
    letterSpacing: 0.5,
  },
  titleFr: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 17,
    color: colors.white,
    textAlign: 'center',
  },
  titleEn: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    // Dimmer white for the secondary (non-chosen) language label
    color: 'rgba(255,255,255,0.5)',
    textAlign: 'center',
    marginTop: 4,
  },

  // Language option cards
  cards: {
    paddingHorizontal: 24,
    gap: 12,
    marginBottom: 36,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    // Subtle frosted-glass feel on the navy background
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderRadius: 16,
    paddingHorizontal: 20,
    paddingVertical: 22,
    borderWidth: 2,
    borderColor: 'transparent',
    minHeight: 80,
  },
  cardSelected: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderColor: colors.teal, // teal ring when selected
  },
  flag: {
    fontSize: 34,
    marginRight: 18,
  },
  cardText: {
    flex: 1,
  },
  cardPrimary: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 17,
    color: 'rgba(255,255,255,0.65)',
  },
  cardPrimarySelected: {
    color: colors.white, // brighter when selected
  },
  cardSecondary: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: 'rgba(255,255,255,0.38)',
    marginTop: 3,
  },

  // Radio button indicator
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioSelected: {
    borderColor: colors.teal,
  },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.teal,
  },

  // Bottom action area
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 16,
  },
});
