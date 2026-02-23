import { StyleSheet } from 'react-native';

export const colors = {
  bg: '#09090B',
  card: '#18181B',
  cardHighlight: '#27272A',
  primary: '#7C3AED',
  accent: '#8B5CF6',
  aiGlow: '#A78BFA',
  profit: '#10B981',
  loss: '#EF4444',
  warning: '#F59E0B',
  info: '#3B82F6',
  neutral: '#71717A',
  text: '#FFFFFF',
  textSecondary: '#A1A1AA',
  textMuted: '#71717A',
  border: '#27272A',
  borderActive: '#3F3F46',
};

export const shared = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(39,39,42,0.5)',
    marginBottom: 16,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 16,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  badge: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 20,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
});

export function formatCurrency(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return '₹' + val.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

export function formatLargeNumber(val: number | null | undefined): string {
  if (!val) return '—';
  if (val >= 1e12) return `₹${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e7) return `₹${(val / 1e7).toFixed(2)}Cr`;
  if (val >= 1e5) return `₹${(val / 1e5).toFixed(2)}L`;
  return formatCurrency(val);
}
