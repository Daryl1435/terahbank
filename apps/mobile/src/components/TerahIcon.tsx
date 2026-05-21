/**
 * TerahIcon — wraps Ionicons from @expo/vector-icons.
 *
 * Every icon in the app should come through here so the underlying
 * icon library stays swappable without touching every screen.
 *
 * @expo/vector-icons ships with Expo SDK 54 — no extra install needed.
 *
 * Usage:
 *   <TerahIcon name="notifications-outline" size={22} color={colors.white} />
 *   <TerahIcon name="chevron-forward" size={18} color={colors.midGrey} />
 */
import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '@/utils/tokens';

// Re-export the icon name type so callers get autocomplete
export type TerahIconName = React.ComponentProps<typeof Ionicons>['name'];

interface TerahIconProps {
  name:   TerahIconName;
  size?:  number;
  color?: string;
}

export function TerahIcon({ name, size = 24, color = colors.navy }: TerahIconProps) {
  return <Ionicons name={name} size={size} color={color} />;
}
