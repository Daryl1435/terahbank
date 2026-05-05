/**
 * TerahLogo — renders the TerahBank logo using react-native-svg primitives.
 * Source: asserts/terahbanklogo-full.svg and asserts/terahbanklogo-symbol.svg
 *
 * Usage:
 *   <TerahLogo variant="full"   width={200} />   // full wordmark
 *   <TerahLogo variant="symbol" width={48}  />   // shield icon only
 */
import React from 'react';
import Svg, { Path, Rect, Circle, Text, TSpan, G } from 'react-native-svg';

interface TerahLogoProps {
  variant?: 'full' | 'symbol';
  width?: number;
  onDark?: boolean;
}

export function TerahLogo({ variant = 'full', width = 180, onDark = false }: TerahLogoProps) {
  const shieldFill = onDark ? '#FFFFFF' : '#0B1F4A';
  const wordmarkFill = onDark ? '#FFFFFF' : '#0B1F4A';

  if (variant === 'symbol') {
    const height = Math.round(width * 1.1);
    return (
      <Svg width={width} height={height} viewBox="0 0 100 110">
        <G>
          {/* Shield body */}
          <Path
            d="M10,8 L90,8 L90,62 C90,90 50,106 50,106 C50,106 10,90 10,62 Z"
            fill={shieldFill}
          />
          {/* Teal accent bar at top */}
          <Rect x="10" y="8" width="80" height="11" rx="3" fill="#00B4D8" />
          {/* T — horizontal bar */}
          <Rect x="28" y="36" width="44" height="9" rx="3" fill="white" />
          {/* T — vertical bar */}
          <Rect x="41" y="45" width="18" height="32" rx="3" fill="white" />
          {/* Teal dot at shield base */}
          <Circle cx="50" cy="92" r="6" fill="#00B4D8" />
        </G>
      </Svg>
    );
  }

  // Full logo: shield + wordmark "TerahBank" + tagline
  const height = Math.round(width * 0.4);
  return (
    <Svg width={width} height={height} viewBox="0 0 400 160">
      <G>
        {/* Shield body */}
        <Path
          d="M20,18 L70,18 L70,70 C70,95 45,110 45,110 C45,110 20,95 20,70 Z"
          fill={shieldFill}
        />
        {/* Teal accent bar on shield top */}
        <Rect x="20" y="18" width="50" height="8" rx="2" fill="#00B4D8" />
        {/* T letter — horizontal bar */}
        <Rect x="33" y="40" width="24" height="5" rx="2" fill="white" />
        {/* T letter — vertical bar */}
        <Rect x="43" y="45" width="5" height="30" rx="2" fill="white" />
        {/* Teal dot at shield base */}
        <Circle cx="45" cy="95" r="4" fill="#00B4D8" />
      </G>

      {/* Wordmark */}
      <Text
        x="88"
        y="82"
        fontFamily="Poppins_700Bold"
        fontWeight="700"
        fontSize="44"
        letterSpacing="-1"
      >
        <TSpan fill={wordmarkFill}>Terah</TSpan>
        <TSpan fill="#00B4D8">Bank</TSpan>
      </Text>

      {/* Tagline */}
      <Text
        x="89"
        y="104"
        fontFamily="Roboto_400Regular"
        fontWeight="400"
        fontSize="13"
        fill="#6B7A99"
        letterSpacing="2.5"
      >
        SAVE. GROW. THRIVE
      </Text>

      {/* Teal underline accent */}
      <Rect x="89" y="112" width="60" height="2.5" rx="1.5" fill="#00B4D8" />
    </Svg>
  );
}
