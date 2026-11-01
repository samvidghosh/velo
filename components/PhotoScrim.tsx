import React from 'react';
import { StyleSheet, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

export default function PhotoScrim({ variant = 'welcome' }: { variant?: 'welcome' | 'login' | 'story' }) {
  const verticalColors = variant === 'story'
    ? ['rgba(3,8,13,0.32)', 'rgba(3,8,13,0.06)', 'rgba(3,8,13,0.8)', '#05090E'] as const
    : variant === 'login'
      ? ['rgba(5,8,12,0.34)', 'rgba(5,8,12,0.16)', 'rgba(8,9,10,0.7)'] as const
      : ['rgba(5,9,13,0.22)', 'rgba(7,10,13,0.03)', 'rgba(7,9,10,0.2)', 'rgba(7,8,9,0.92)'] as const;
  const verticalLocations = variant === 'story' ? [0, .3, .72, 1] as const : variant === 'login' ? [0, .36, 1] as const : [0, .27, .48, 1] as const;
  const horizontalShade = variant === 'login' ? 'rgba(6,10,14,0.4)' : variant === 'welcome' ? 'rgba(4,8,12,0.38)' : 'rgba(4,9,14,0.2)';
  return <View pointerEvents="none" style={StyleSheet.absoluteFill}>
    <LinearGradient colors={verticalColors} locations={verticalLocations} start={{ x: 0, y: 0 }} end={{ x: 0, y: 1 }} style={StyleSheet.absoluteFill} />
    <LinearGradient colors={[horizontalShade, 'transparent']} locations={[0, variant === 'login' ? .72 : .75]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={StyleSheet.absoluteFill} />
  </View>;
}
