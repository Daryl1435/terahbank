/**
 * ChannelLogo — renders a branded logo badge for each payment channel.
 * Falls back to a styled view using official brand colors when image assets
 * are not present. Replace with Image components once logo PNGs are placed in
 * assets/logos/.
 */
import React from 'react';
import { Image, View, Text, StyleSheet } from 'react-native';

export type PaymentChannel = 'mtn_momo' | 'orange_money' | 'visa' | 'mastercard' | 'internal';

interface ChannelLogoProps {
  channel: PaymentChannel;
  size?: number;
}

// Try to load assets — if not present the require will be caught and we fall back.
// Place real logo files at assets/logos/mtn-momo.png and assets/logos/orange-money.png
let MTN_LOGO: number | null = null;
let ORANGE_LOGO: number | null = null;

try { MTN_LOGO    = require('../../assets/logos/mtn-momo.png');    } catch { /* no asset yet */ }
try { ORANGE_LOGO = require('../../assets/logos/orange-money.png'); } catch { /* no asset yet */ }

// ── Brand fallback colors ─────────────────────────────────────────────────────

const BRANDS: Record<PaymentChannel, { bg: string; text: string; label: string }> = {
  mtn_momo:     { bg: '#0066B3', text: '#FFCC00', label: 'MoMo' },
  orange_money: { bg: '#FFFFFF', text: '#FF6600', label: 'OM'   },
  visa:         { bg: '#1A1F71', text: '#FFFFFF', label: 'VISA' },
  mastercard:   { bg: '#EB001B', text: '#FFFFFF', label: 'MC'   },
  internal:     { bg: '#E8EDF5', text: '#0B1F4A', label: 'TB'   },
};

export function ChannelLogo({ channel, size = 40 }: ChannelLogoProps) {
  const radius   = size * 0.25;
  const fontSize = size * 0.28;
  const brand    = BRANDS[channel] ?? BRANDS.internal;

  // Use real image asset when available
  if (channel === 'mtn_momo' && MTN_LOGO) {
    return (
      <Image
        source={MTN_LOGO}
        style={{ width: size, height: size, borderRadius: radius }}
        resizeMode="contain"
      />
    );
  }
  if (channel === 'orange_money' && ORANGE_LOGO) {
    return (
      <Image
        source={ORANGE_LOGO}
        style={{ width: size, height: size, borderRadius: radius }}
        resizeMode="contain"
      />
    );
  }

  // Styled fallback
  return (
    <View
      style={[
        styles.badge,
        {
          width: size,
          height: size,
          borderRadius: radius,
          backgroundColor: brand.bg,
          borderWidth: channel === 'orange_money' || channel === 'internal' ? 1 : 0,
          borderColor: '#E8EDF5',
        },
      ]}
    >
      {channel === 'mtn_momo' ? (
        // MTN MoMo — yellow "M" on blue
        <Text style={[styles.text, { fontSize, color: brand.text, fontFamily: 'Poppins_700Bold' }]}>
          {brand.label}
        </Text>
      ) : channel === 'orange_money' ? (
        // Orange Money — orange arrows ↗↙ style
        <View style={styles.arrowWrap}>
          <Text style={[styles.arrow, { fontSize: fontSize * 1.1, color: '#000000' }]}>↗</Text>
          <Text style={[styles.arrow, { fontSize: fontSize * 1.1, color: '#FF6600' }]}>↙</Text>
        </View>
      ) : (
        <Text style={[styles.text, { fontSize, color: brand.text, fontFamily: 'Poppins_700Bold' }]}>
          {brand.label}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  text: {
    lineHeight: undefined,
    textAlign: 'center',
  },
  arrowWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  arrow: {
    lineHeight: undefined,
    marginHorizontal: -1,
  },
});
