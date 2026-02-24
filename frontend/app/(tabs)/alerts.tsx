import React, { useEffect, useState, useCallback } from 'react';
import {
    View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Alert, TextInput, Modal
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api';
import { colors, formatCurrency } from '../../src/theme';

export default function AlertsScreen() {
    const [alerts, setAlerts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [evaluating, setEvaluating] = useState(false);

    // Modal State
    const [showModal, setShowModal] = useState(false);
    const [newSymbol, setNewSymbol] = useState('');
    const [newPrice, setNewPrice] = useState('');
    const [newCondition, setNewCondition] = useState<'above' | 'below'>('above');
    const [creating, setCreating] = useState(false);

    const fetchAlerts = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getAlerts();
            setAlerts(res.alerts || []);
        } catch (e: any) {
            Alert.alert('Error', e.message || 'Failed to load alerts');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAlerts();
    }, [fetchAlerts]);

    const handleCreateAlert = async () => {
        if (!newSymbol || !newPrice) {
            Alert.alert('Validation Error', 'Symbol and Target Price are required.');
            return;
        }
        setCreating(true);
        try {
            await api.createAlert({
                symbol: newSymbol.toUpperCase(),
                target_price: parseFloat(newPrice),
                condition: newCondition
            });
            setShowModal(false);
            setNewSymbol('');
            setNewPrice('');
            fetchAlerts();
        } catch (e: any) {
            Alert.alert('Error', e.message || 'Failed to create alert');
        } finally {
            setCreating(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await api.deleteAlert(id);
            fetchAlerts();
        } catch (e: any) {
            Alert.alert('Error', e.message || 'Failed to delete alert');
        }
    };

    const handleEvaluate = async () => {
        setEvaluating(true);
        try {
            const res = await api.evaluateAlerts();
            if (res.triggered && res.triggered.length > 0) {
                Alert.alert(
                    'Alerts Triggered!',
                    `The following alerts were triggered just now:\n\n${res.triggered.map((t: any) => `${t.symbol} crossed ${t.target_price}`).join('\n')}`
                );
                fetchAlerts(); // Refresh list to remove triggered ones (they become inactive)
            } else {
                Alert.alert('No Alerts Triggered', 'None of your active alerts met their conditions currently.');
            }
        } catch (e: any) {
            Alert.alert('Error', e.message || 'Failed to evaluate alerts');
        } finally {
            setEvaluating(false);
        }
    };

    const renderItem = ({ item }: { item: any }) => (
        <View style={styles.alertCard}>
            <View style={styles.alertInfo}>
                <Text style={styles.symbolText}>{item.symbol.replace('.NS', '').replace('.BO', '')}</Text>
                <View style={styles.conditionRow}>
                    <Text style={styles.conditionText}>
                        When price goes <Text style={{ color: item.condition === 'above' ? colors.profit : colors.loss, fontWeight: '700' }}>
                            {item.condition.toUpperCase()}
                        </Text> {formatCurrency(item.target_price)}
                    </Text>
                </View>
                <Text style={styles.dateText}>Created: {new Date(item.created_at).toLocaleDateString()}</Text>
            </View>
            <TouchableOpacity style={styles.deleteBtn} onPress={() => handleDelete(item._id)}>
                <Ionicons name="trash-outline" size={20} color={colors.loss} />
            </TouchableOpacity>
        </View>
    );

    return (
        <SafeAreaView style={styles.screen}>
            <View style={styles.header}>
                <View>
                    <Text style={styles.title}>Price Alerts</Text>
                    <Text style={styles.subtitle}>Set alerts and evaluate them against live prices</Text>
                </View>
                <TouchableOpacity style={styles.evalBtn} onPress={handleEvaluate} disabled={evaluating}>
                    {evaluating ? (
                        <ActivityIndicator size="small" color="#FFF" />
                    ) : (
                        <Ionicons name="scan-outline" size={24} color="#FFF" />
                    )}
                </TouchableOpacity>
            </View>

            {loading ? (
                <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></View>
            ) : (
                <FlatList
                    data={alerts}
                    keyExtractor={(item) => item._id}
                    renderItem={renderItem}
                    contentContainerStyle={styles.listContent}
                    ListEmptyComponent={
                        <View style={styles.emptyState}>
                            <Ionicons name="notifications-off-outline" size={48} color={colors.textMuted} />
                            <Text style={styles.emptyText}>No active alerts found.</Text>
                        </View>
                    }
                />
            )}

            <TouchableOpacity style={styles.fab} onPress={() => setShowModal(true)}>
                <Ionicons name="add" size={30} color="#FFF" />
            </TouchableOpacity>

            {/* New Alert Modal */}
            <Modal visible={showModal} transparent animationType="slide">
                <View style={styles.modalBg}>
                    <View style={styles.modalContainer}>
                        <View style={styles.modalHeader}>
                            <Text style={styles.modalTitle}>Create Alert</Text>
                            <TouchableOpacity onPress={() => setShowModal(false)}>
                                <Ionicons name="close" size={24} color={colors.textMuted} />
                            </TouchableOpacity>
                        </View>

                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Stock Symbol (e.g., RELIANCE.NS)</Text>
                            <TextInput
                                style={styles.input}
                                placeholder="RELIANCE.NS"
                                placeholderTextColor={colors.textMuted}
                                value={newSymbol}
                                onChangeText={setNewSymbol}
                                autoCapitalize="characters"
                            />
                        </View>

                        <View style={styles.inputGroup}>
                            <Text style={styles.label}>Target Price (₹)</Text>
                            <TextInput
                                style={styles.input}
                                placeholder="2500"
                                placeholderTextColor={colors.textMuted}
                                value={newPrice}
                                onChangeText={setNewPrice}
                                keyboardType="numeric"
                            />
                        </View>

                        <View style={styles.conditionToggle}>
                            <TouchableOpacity
                                style={[styles.toggleBtn, newCondition === 'above' && styles.toggleBtnActiveGreen]}
                                onPress={() => setNewCondition('above')}
                            >
                                <Text style={[styles.toggleText, newCondition === 'above' && styles.toggleTextActive]}>ABOVE</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.toggleBtn, newCondition === 'below' && styles.toggleBtnActiveRed]}
                                onPress={() => setNewCondition('below')}
                            >
                                <Text style={[styles.toggleText, newCondition === 'below' && styles.toggleTextActive]}>BELOW</Text>
                            </TouchableOpacity>
                        </View>

                        <TouchableOpacity style={styles.saveBtn} onPress={handleCreateAlert} disabled={creating}>
                            {creating ? <ActivityIndicator color="#FFF" /> : <Text style={styles.saveBtnText}>Save Alert</Text>}
                        </TouchableOpacity>
                    </View>
                </View>
            </Modal>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bg },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
    header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 12, paddingBottom: 20 },
    title: { color: colors.text, fontSize: 28, fontWeight: '800' },
    subtitle: { color: colors.textMuted, fontSize: 13, marginTop: 4 },
    evalBtn: { backgroundColor: colors.primary, width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
    listContent: { paddingHorizontal: 20, paddingBottom: 100 },
    alertCard: { backgroundColor: colors.card, borderRadius: 16, padding: 16, marginBottom: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderWidth: 1, borderColor: 'rgba(39,39,42,0.5)' },
    alertInfo: { flex: 1 },
    symbolText: { color: colors.text, fontSize: 18, fontWeight: '700' },
    conditionRow: { flexDirection: 'row', marginTop: 6, alignItems: 'center' },
    conditionText: { color: colors.textSecondary, fontSize: 14 },
    dateText: { color: colors.textMuted, fontSize: 12, marginTop: 8 },
    deleteBtn: { padding: 10, backgroundColor: 'rgba(239,68,68,0.1)', borderRadius: 10 },
    emptyState: { alignItems: 'center', marginTop: 100 },
    emptyText: { color: colors.textMuted, marginTop: 16, fontSize: 16 },
    fab: { position: 'absolute', bottom: 30, right: 20, width: 60, height: 60, borderRadius: 30, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center', shadowColor: colors.accent, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 5 },
    modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
    modalContainer: { backgroundColor: colors.card, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 40 },
    modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
    modalTitle: { color: colors.text, fontSize: 20, fontWeight: '700' },
    inputGroup: { marginBottom: 20 },
    label: { color: colors.textSecondary, fontSize: 13, marginBottom: 8, fontWeight: '600' },
    input: { backgroundColor: 'rgba(39,39,42,0.4)', color: colors.text, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, borderWidth: 1, borderColor: 'rgba(39,39,42,0.8)' },
    conditionToggle: { flexDirection: 'row', gap: 12, marginBottom: 24 },
    toggleBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, alignItems: 'center', backgroundColor: 'rgba(39,39,42,0.4)', borderWidth: 1, borderColor: 'transparent' },
    toggleBtnActiveGreen: { backgroundColor: 'rgba(16,185,129,0.15)', borderColor: colors.profit },
    toggleBtnActiveRed: { backgroundColor: 'rgba(239,68,68,0.15)', borderColor: colors.loss },
    toggleText: { color: colors.textMuted, fontSize: 14, fontWeight: '700' },
    toggleTextActive: { color: colors.text },
    saveBtn: { backgroundColor: colors.primary, borderRadius: 14, paddingVertical: 16, alignItems: 'center' },
    saveBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
