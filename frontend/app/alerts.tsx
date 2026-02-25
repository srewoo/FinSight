/**
 * Price Alerts Screen
 * Allows users to create, view, and manage price alerts.
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  Modal,
  TextInput,
  ActivityIndicator,
  Alert,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../src/api';
import { useTheme } from '../src/theme';

interface Alert {
  id: string;
  symbol: string;
  target_price: number;
  condition: string;
  current_price?: number;
  triggered: boolean;
  triggered_at?: string;
  note: string;
  created_at: string;
}

export default function AlertsScreen() {
  const theme = useTheme();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [triggeredAlerts, setTriggeredAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [symbol, setSymbol] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [condition, setCondition] = useState<'above' | 'below'>('above');

  const loadAlerts = async () => {
    try {
      const [activeData, triggeredData] = await Promise.all([
        api.getAlerts(true),
        api.getTriggeredAlerts(),
      ]);
      setAlerts(activeData.alerts || []);
      setTriggeredAlerts(triggeredData.alerts || []);
    } catch (err: any) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadAlerts();
  };

  const handleCreateAlert = async () => {
    if (!symbol.trim() || !targetPrice) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    try {
      const upperSymbol = symbol.toUpperCase().trim();
      // Auto-append .NS if not present
      const finalSymbol = upperSymbol.includes('.') ? upperSymbol : `${upperSymbol}.NS`;
      
      await api.createAlert({
        symbol: finalSymbol,
        target_price: parseFloat(targetPrice),
        condition,
        note: '',
      });
      
      Alert.alert('Success', 'Alert created successfully');
      setModalVisible(false);
      setSymbol('');
      setTargetPrice('');
      loadAlerts();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to create alert');
    }
  };

  const handleDeleteAlert = async (id: string) => {
    Alert.alert('Delete Alert', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.deleteAlert(id);
            loadAlerts();
          } catch (err: any) {
            Alert.alert('Error', err.message || 'Failed to delete alert');
          }
        },
      },
    ]);
  };

  const handleMarkRead = async (id: string) => {
    try {
      await api.markAlertRead(id);
      loadAlerts();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to mark as read');
    }
  };

  const renderAlertItem = ({ item }: { item: Alert }) => (
    <View style={[styles.alertCard, { backgroundColor: theme.cardBg, borderColor: theme.border }]}>
      <View style={styles.alertHeader}>
        <View>
          <Text style={[styles.alertSymbol, { color: theme.text }]}>{item.symbol}</Text>
          <Text style={[styles.alertNote, { color: theme.textMuted }]}>
            {item.note || 'Price alert'}
          </Text>
        </View>
        {item.triggered && (
          <View style={styles.triggeredBadge}>
            <Text style={styles.triggeredText}>TRIGGERED</Text>
          </View>
        )}
      </View>

      <View style={styles.alertBody}>
        <View style={styles.alertCondition}>
          <Ionicons
            name={item.condition === 'above' ? 'arrow-up' : 'arrow-down'}
            size={16}
            color={item.condition === 'above' ? theme.success : theme.danger}
          />
          <Text style={[styles.conditionText, { color: theme.text }]}>
            {item.condition === 'above' ? 'Above' : 'Below'} ₹{item.target_price}
          </Text>
        </View>

        {item.current_price && (
          <Text style={[styles.currentPrice, { color: theme.textMuted }]}>
            Current: ₹{item.current_price.toFixed(2)}
          </Text>
        )}
      </View>

      <View style={styles.alertFooter}>
        <Text style={[styles.alertTime, { color: theme.textMuted }]}>
          {item.triggered_at
            ? `Triggered: ${new Date(item.triggered_at).toLocaleString()}`
            : `Created: ${new Date(item.created_at).toLocaleString()}`}
        </Text>

        <View style={styles.alertActions}>
          {item.triggered && (
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: theme.primary }]}
              onPress={() => handleMarkRead(item.id)}
            >
              <Ionicons name="checkmark" size={18} color="#fff" />
            </TouchableOpacity>
          )}
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: theme.danger }]}
            onPress={() => handleDeleteAlert(item.id)}
          >
            <Ionicons name="trash" size={18} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.bg }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textMuted }]}>Loading alerts...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.bg }]}>
      <View style={styles.header}>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Price Alerts</Text>
        <TouchableOpacity
          style={[styles.addButton, { backgroundColor: theme.primary }]}
          onPress={() => setModalVisible(true)}
        >
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      {triggeredAlerts.length > 0 && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            Triggered Alerts ({triggeredAlerts.length})
          </Text>
          <FlatList
            data={triggeredAlerts}
            renderItem={renderAlertItem}
            keyExtractor={(item) => item.id}
            scrollEnabled={false}
            contentContainerStyle={styles.listContent}
          />
        </View>
      )}

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>
          Active Alerts ({alerts.length})
        </Text>
        <FlatList
          data={alerts}
          renderItem={renderAlertItem}
          keyExtractor={(item) => item.id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
          }
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Ionicons name="notifications-off-outline" size={48} color={theme.textMuted} />
              <Text style={[styles.emptyText, { color: theme.textMuted }]}>
                No active alerts. Create one to get notified!
              </Text>
            </View>
          }
        />
      </View>

      {/* Create Alert Modal */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: theme.cardBg }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: theme.text }]}>Create Price Alert</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={28} color={theme.text} />
              </TouchableOpacity>
            </View>

            <View style={styles.modalBody}>
              <View style={styles.inputGroup}>
                <Text style={[styles.label, { color: theme.text }]}>Stock Symbol</Text>
                <TextInput
                  style={[styles.input, { backgroundColor: theme.inputBg, color: theme.text, borderColor: theme.border }]}
                  placeholder="e.g., RELIANCE"
                  placeholderTextColor={theme.textMuted}
                  value={symbol}
                  onChangeText={setSymbol}
                  autoCapitalize="characters"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={[styles.label, { color: theme.text }]}>Target Price (₹)</Text>
                <TextInput
                  style={[styles.input, { backgroundColor: theme.inputBg, color: theme.text, borderColor: theme.border }]}
                  placeholder="0.00"
                  placeholderTextColor={theme.textMuted}
                  value={targetPrice}
                  onChangeText={setTargetPrice}
                  keyboardType="decimal-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={[styles.label, { color: theme.text }]}>Condition</Text>
                <View style={styles.conditionButtons}>
                  <TouchableOpacity
                    style={[
                      styles.conditionButton,
                      { backgroundColor: condition === 'above' ? theme.success : theme.inputBg },
                    ]}
                    onPress={() => setCondition('above')}
                  >
                    <Ionicons
                      name="arrow-up"
                      size={20}
                      color={condition === 'above' ? '#fff' : theme.text}
                    />
                    <Text
                      style={[
                        styles.conditionButtonText,
                        { color: condition === 'above' ? '#fff' : theme.text },
                      ]}
                    >
                      Above
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.conditionButton,
                      { backgroundColor: condition === 'below' ? theme.danger : theme.inputBg },
                    ]}
                    onPress={() => setCondition('below')}
                  >
                    <Ionicons
                      name="arrow-down"
                      size={20}
                      color={condition === 'below' ? '#fff' : theme.text}
                    />
                    <Text
                      style={[
                        styles.conditionButtonText,
                        { color: condition === 'below' ? '#fff' : theme.text },
                      ]}
                    >
                      Below
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>

            <TouchableOpacity
              style={[styles.createButton, { backgroundColor: theme.primary }]}
              onPress={handleCreateAlert}
            >
              <Text style={styles.createButtonText}>Create Alert</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = {
  container: {
    flex: 1,
  } as any,
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  } as any,
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
  } as any,
  addButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  } as any,
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  } as any,
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  } as any,
  section: {
    marginTop: 16,
  } as any,
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    paddingHorizontal: 16,
    marginBottom: 12,
  } as any,
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 16,
  } as any,
  alertCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  } as any,
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  } as any,
  alertSymbol: {
    fontSize: 18,
    fontWeight: 'bold',
  } as any,
  alertNote: {
    fontSize: 14,
    marginTop: 2,
  } as any,
  triggeredBadge: {
    backgroundColor: '#EF4444',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  } as any,
  triggeredText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  } as any,
  alertBody: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  } as any,
  alertCondition: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  } as any,
  conditionText: {
    fontSize: 16,
    fontWeight: '500',
  } as any,
  currentPrice: {
    fontSize: 14,
  } as any,
  alertFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  } as any,
  alertTime: {
    fontSize: 12,
  } as any,
  alertActions: {
    flexDirection: 'row',
    gap: 8,
  } as any,
  actionButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  } as any,
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
  } as any,
  emptyText: {
    fontSize: 16,
    marginTop: 16,
    textAlign: 'center',
  } as any,
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'flex-end',
  } as any,
  modalContent: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingBottom: 40,
  } as any,
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
  } as any,
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
  } as any,
  modalBody: {
    padding: 20,
  } as any,
  inputGroup: {
    marginBottom: 20,
  } as any,
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  } as any,
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
  } as any,
  conditionButtons: {
    flexDirection: 'row',
    gap: 12,
  } as any,
  conditionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
  } as any,
  conditionButtonText: {
    fontSize: 16,
    fontWeight: '600',
  } as any,
  createButton: {
    marginHorizontal: 20,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  } as any,
  createButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  } as any,
};
