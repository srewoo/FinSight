import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme';

const SEBI_SHORT_TEXT =
  'Not SEBI-registered. AI analysis is for informational purposes only. ' +
  'Past performance does not guarantee future results. Invest at your own risk.';

export default function SEBIDisclaimerBanner() {
  return (
    <View style={styles.container}>
      <Ionicons name="warning" size={14} color={colors.warning} />
      <Text style={styles.text}>{SEBI_SHORT_TEXT}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 16,
    padding: 12,
    backgroundColor: `${colors.warning}10`,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: `${colors.warning}25`,
  },
  text: {
    color: colors.textMuted,
    fontSize: 11,
    lineHeight: 16,
    flex: 1,
  },
});
