import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme';
import { api } from '../api';

const DISCLAIMER_VERSION = '1.0';
const STORAGE_KEY = `sebi_disclaimer_accepted_v${DISCLAIMER_VERSION}`;

const SEBI_FULL_TEXT =
  'IMPORTANT DISCLAIMER: FinSight is NOT a SEBI-registered Investment Adviser ' +
  'under the SEBI (Investment Advisers) Regulations, 2013. The information, ' +
  'analysis, and recommendations provided by this application are generated ' +
  'by artificial intelligence for educational and informational purposes only. ' +
  'They do NOT constitute investment advice, financial advice, trading advice, ' +
  'or any other form of professional advice.\n\n' +
  'Past performance of any stock, index, or AI prediction does not guarantee ' +
  'future results. Stock market investments are subject to market risks. Read ' +
  'all scheme-related documents carefully before investing.\n\n' +
  'You should consult a SEBI-registered investment adviser before making any ' +
  'investment decisions. By using AI-powered features of this app, you ' +
  'acknowledge and accept that you are solely responsible for your investment ' +
  'decisions and any gains or losses resulting from them.';

interface Props {
  onAccepted?: () => void;
  children: React.ReactNode;
}

export default function SEBIDisclaimerGate({ onAccepted, children }: Props) {
  const [accepted, setAccepted] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((val) => {
      setAccepted(val === 'true');
    });
  }, []);

  const handleAccept = async () => {
    setSubmitting(true);
    try {
      await api.acceptDisclaimer(DISCLAIMER_VERSION);
    } catch {
      // Still allow local acceptance even if backend call fails
    }
    await AsyncStorage.setItem(STORAGE_KEY, 'true');
    setAccepted(true);
    setSubmitting(false);
    onAccepted?.();
  };

  // Still loading acceptance state
  if (accepted === null) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="small" color={colors.primary} />
      </View>
    );
  }

  // Already accepted — render children
  if (accepted) {
    return <>{children}</>;
  }

  // Show modal
  return (
    <>
      {children}
      <Modal visible transparent animationType="fade">
        <View style={styles.overlay}>
          <View style={styles.modal}>
            <View style={styles.header}>
              <Ionicons name="shield-checkmark" size={28} color={colors.warning} />
              <Text style={styles.title}>Regulatory Disclaimer</Text>
            </View>

            <ScrollView
              style={styles.scrollArea}
              contentContainerStyle={styles.scrollContent}
              showsVerticalScrollIndicator
            >
              <Text style={styles.disclaimerText}>{SEBI_FULL_TEXT}</Text>
            </ScrollView>

            <View style={styles.footer}>
              <Text style={styles.footerNote}>
                By tapping "I Understand & Accept", you confirm you have read and understood this disclaimer.
              </Text>
              <TouchableOpacity
                style={[styles.acceptBtn, submitting && { opacity: 0.6 }]}
                onPress={handleAccept}
                disabled={submitting}
                activeOpacity={0.8}
              >
                {submitting ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <>
                    <Ionicons name="checkmark-circle" size={18} color="#fff" />
                    <Text style={styles.acceptBtnText}>I Understand & Accept</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.bg,
  },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modal: {
    backgroundColor: colors.card,
    borderRadius: 20,
    width: '100%',
    maxHeight: '80%',
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.text,
  },
  scrollArea: {
    maxHeight: 300,
  },
  scrollContent: {
    padding: 20,
  },
  disclaimerText: {
    fontSize: 13,
    lineHeight: 20,
    color: colors.textSecondary,
  },
  footer: {
    padding: 20,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: 12,
  },
  footerNote: {
    fontSize: 11,
    color: colors.textMuted,
    lineHeight: 16,
  },
  acceptBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: colors.primary,
    borderRadius: 14,
    paddingVertical: 14,
  },
  acceptBtnText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#fff',
  },
});
