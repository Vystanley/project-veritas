import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  Alert, ActivityIndicator, TextInput, Modal, Share, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import * as WebBrowser from 'expo-web-browser';
import { useAuth } from '../components/AuthContext';
import { colors, fonts, radius, spacing } from '../constants/theme';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface SubStatus {
  plan: string; scans_used: number; scans_remaining: number;
  is_premium: boolean; expires_at: string | null; period_resets_at: string; bonus_scans: number;
}

interface ReferralInfo {
  code: string; referred_count: number; bonus_scans_earned: number;
}

export default function SettingsScreen() {
  const { user, token, logout, loading } = useAuth();
  const router = useRouter();
  const [subStatus, setSubStatus] = useState<SubStatus | null>(null);
  const [referral, setReferral] = useState<ReferralInfo | null>(null);
  const [referralInput, setReferralInput] = useState('');
  const [applyingCode, setApplyingCode] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [renewing, setRenewing] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace('/');
  }, [user, loading]);

  useEffect(() => {
    if (token) { fetchSubscription(); fetchReferral(); }
  }, [token]);

  const fetchSubscription = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/subscription/status`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setSubStatus(await res.json());
    } catch {}
  }, [token]);

  const fetchReferral = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/referral/info`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setReferral(await res.json());
    } catch {}
  }, [token]);

  if (loading || !user) {
    return <View style={s.loadingContainer}><ActivityIndicator size="large" color={colors.accent} /></View>;
  }

  async function handleCancelSubscription() {
    setCancelling(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/subscription/cancel`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        Alert.alert('Subscription Cancelled', 'You have been downgraded to the free plan.');
        setShowCancelConfirm(false);
        fetchSubscription();
      }
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Could not cancel subscription');
    } finally { setCancelling(false); }
  }

  async function handleRenew(plan: string) {
    setRenewing(true);
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : BACKEND_URL;
      const res = await fetch(`${BACKEND_URL}/api/payments/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ plan, origin_url: origin }),
      });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail); }
      const data = await res.json();
      if (Platform.OS === 'web') { window.location.href = data.url; }
      else { await WebBrowser.openBrowserAsync(data.url); fetchSubscription(); }
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Checkout failed');
    } finally { setRenewing(false); }
  }

  async function handleCopyReferral() {
    if (referral?.code) {
      await Clipboard.setStringAsync(referral.code);
      Alert.alert('Copied!', 'Referral code copied to clipboard');
    }
  }

  async function handleShareReferral() {
    if (referral?.code) {
      await Share.share({
        message: `Join Veritas - AI Video Fact Checker! Use my referral code: ${referral.code} to get 3 bonus scans!`,
        title: 'Invite to Veritas',
      });
    }
  }

  async function handleApplyReferral() {
    if (!referralInput.trim()) { Alert.alert('Error', 'Please enter a referral code'); return; }
    setApplyingCode(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/referral/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ referral_code: referralInput.trim() }),
      });
      const data = await res.json();
      if (res.ok) {
        Alert.alert('Success!', data.message || 'Bonus scans added!');
        setReferralInput('');
        fetchReferral();
        fetchSubscription();
      } else {
        Alert.alert('Error', data.detail || 'Could not apply code');
      }
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally { setApplyingCode(false); }
  }

  const scansText = subStatus
    ? subStatus.is_premium
      ? `${subStatus.scans_remaining} scans left this month`
      : `${subStatus.scans_remaining}/${2 + subStatus.bonus_scans} free scans this week`
    : '';

  const expiresDate = subStatus?.expires_at ? new Date(subStatus.expires_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : null;

  return (
    <SafeAreaView style={s.container}>
      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={s.header}>
          <TouchableOpacity testID="settings-back-btn" style={s.backBtn} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={20} color={colors.text} />
          </TouchableOpacity>
          <Text style={s.headerTitle}>Settings</Text>
          <View style={{ width: 44 }} />
        </View>

        {/* Profile Section */}
        <View style={s.profileSection}>
          <View style={s.avatarWrap}>
            <Text style={s.avatarText}>{user.name.charAt(0).toUpperCase()}</Text>
          </View>
          <Text style={s.userName}>{user.name}</Text>
          <Text style={s.userEmail}>{user.email}</Text>
        </View>

        {/* Plan & Scans Card (moved from home) */}
        <View style={s.card}>
          <View style={s.cardHeader}>
            <Text style={s.cardTitle}>Plan</Text>
            <View style={[s.planBadge, subStatus?.is_premium && s.premiumBadge]}>
              <Text style={[s.planBadgeText, subStatus?.is_premium && s.premiumBadgeText]}>
                {subStatus?.is_premium ? 'PREMIUM' : 'FREE'}
              </Text>
            </View>
          </View>

          {subStatus?.is_premium && expiresDate && (
            <Text style={s.expiresText}>Renews {expiresDate}</Text>
          )}

          <View style={s.statsRow}>
            <View style={s.statItem}>
              <Text style={s.statValue}>{subStatus?.scans_used ?? 0}</Text>
              <Text style={s.statLabel}>Used</Text>
            </View>
            <View style={s.statDivider} />
            <View style={s.statItem}>
              <Text style={[s.statValue, { color: colors.accent }]}>{subStatus?.scans_remaining ?? 0}</Text>
              <Text style={s.statLabel}>Remaining</Text>
            </View>
            <View style={s.statDivider} />
            <View style={s.statItem}>
              <Text style={s.statValue}>{subStatus?.bonus_scans ?? 0}</Text>
              <Text style={s.statLabel}>Bonus</Text>
            </View>
          </View>

          {subStatus && <Text style={s.scansSubtext}>{scansText}</Text>}

          {subStatus?.is_premium ? (
            <TouchableOpacity testID="cancel-sub-btn" style={s.cancelSubBtn} onPress={() => setShowCancelConfirm(true)}>
              <Text style={s.cancelSubBtnText}>Cancel Subscription</Text>
            </TouchableOpacity>
          ) : (
            <View style={s.upgradeBtns}>
              <TouchableOpacity testID="renew-monthly-btn" style={s.upgradeBtn} onPress={() => handleRenew('premium_monthly')} disabled={renewing}>
                {renewing ? <ActivityIndicator size="small" color={colors.accent} /> : (
                  <Text style={s.upgradeBtnText}>Monthly $13.99</Text>
                )}
              </TouchableOpacity>
              <TouchableOpacity testID="renew-annual-btn" style={[s.upgradeBtn, s.upgradeBtnPrimary]} onPress={() => handleRenew('premium_annual')} disabled={renewing}>
                {renewing ? <ActivityIndicator size="small" color={colors.bg} /> : (
                  <Text style={[s.upgradeBtnText, s.upgradeBtnPrimaryText]}>Annual $119/yr — Save 29%</Text>
                )}
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Referral Card */}
        <View style={s.card}>
          <View style={s.cardHeader}>
            <Text style={s.cardTitle}>Referrals</Text>
          </View>
          <Text style={s.referralDesc}>Invite a friend. You both get 3 bonus scans.</Text>

          {referral && (
            <>
              <View style={s.referralCodeRow}>
                <View style={s.referralCodeBox}>
                  <Text style={s.referralCode}>{referral.code}</Text>
                </View>
                <TouchableOpacity testID="copy-referral-btn" style={s.iconBtn} onPress={handleCopyReferral}>
                  <Ionicons name="copy-outline" size={18} color={colors.accent} />
                </TouchableOpacity>
                <TouchableOpacity testID="share-referral-btn" style={s.iconBtn} onPress={handleShareReferral}>
                  <Ionicons name="share-outline" size={18} color={colors.accent} />
                </TouchableOpacity>
              </View>

              <View style={s.referralStats}>
                <Text style={s.referralStatText}>{referral.referred_count} invited</Text>
                <Text style={s.referralStatDot}>·</Text>
                <Text style={s.referralStatText}>{referral.bonus_scans_earned} bonus earned</Text>
              </View>
            </>
          )}

          <View style={s.applyRow}>
            <TextInput testID="referral-code-input" style={s.applyInput} placeholder="Enter friend's code" placeholderTextColor={colors.textMuted} value={referralInput} onChangeText={setReferralInput} autoCapitalize="characters" />
            <TouchableOpacity testID="apply-referral-btn" style={s.applyBtn} onPress={handleApplyReferral} disabled={applyingCode}>
              {applyingCode ? <ActivityIndicator size="small" color={colors.bg} /> : <Text style={s.applyBtnText}>Apply</Text>}
            </TouchableOpacity>
          </View>
        </View>

        {/* Actions */}
        <View style={s.actionsSection}>
          <TouchableOpacity testID="settings-logout-btn" style={s.actionBtn} onPress={() => {
            Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Sign Out', style: 'destructive', onPress: async () => {
                await logout();
                router.replace('/');
              }},
            ]);
          }}>
            <Ionicons name="log-out-outline" size={18} color={colors.error} />
            <Text style={[s.actionBtnText, { color: colors.error }]}>Sign Out</Text>
          </TouchableOpacity>

          <TouchableOpacity testID="delete-account-btn" style={s.actionBtn} onPress={() => {
            Alert.alert(
              'Delete Account',
              'This will permanently delete ALL your data including your account, scan history, subscriptions, and referrals. This action cannot be undone.\n\n(GDPR Right to be Forgotten)',
              [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Delete Everything', style: 'destructive', onPress: async () => {
                  try {
                    const res = await fetch(`${BACKEND_URL}/api/account/delete`, {
                      method: 'DELETE',
                      headers: { Authorization: `Bearer ${token}` },
                    });
                    if (res.ok) {
                      Alert.alert('Account Deleted', 'All your data has been permanently deleted.');
                      await logout();
                      router.replace('/');
                    } else {
                      Alert.alert('Error', 'Could not delete account. Please try again.');
                    }
                  } catch {
                    Alert.alert('Error', 'Could not delete account.');
                  }
                }},
              ]
            );
          }}>
            <Ionicons name="trash-outline" size={18} color={colors.textMuted} />
            <Text style={[s.actionBtnText, { color: colors.textMuted }]}>Delete Account & Data</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Cancel Confirmation Modal */}
      <Modal visible={showCancelConfirm} transparent animationType="fade">
        <View style={s.modalOverlay}>
          <View style={s.modalCard}>
            <Text style={s.modalTitle}>Cancel Subscription?</Text>
            <Text style={s.modalDesc}>You'll lose access to unlimited scans and be downgraded to the free plan (2 scans/week).</Text>
            <View style={s.modalBtns}>
              <TouchableOpacity testID="keep-sub-btn" style={s.keepBtn} onPress={() => setShowCancelConfirm(false)}>
                <Text style={s.keepBtnText}>Keep Plan</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="confirm-cancel-btn" style={s.confirmCancelBtn} onPress={handleCancelSubscription} disabled={cancelling}>
                {cancelling ? <ActivityIndicator color={colors.error} /> : <Text style={s.confirmCancelText}>Cancel</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  loadingContainer: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
  scroll: { paddingHorizontal: 20, paddingBottom: 40 },

  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: 8, marginBottom: 24 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 17, fontFamily: fonts.semiBold, color: colors.text },

  // Profile
  profileSection: { alignItems: 'center', marginBottom: 28 },
  avatarWrap: { width: 56, height: 56, borderRadius: 28, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  avatarText: { fontSize: 22, fontFamily: fonts.semiBold, color: colors.accent },
  userName: { fontSize: 18, fontFamily: fonts.semiBold, color: colors.text },
  userEmail: { fontSize: 14, fontFamily: fonts.regular, color: colors.textSecondary, marginTop: 2 },

  // Card
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: 20, marginBottom: 16 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  cardTitle: { fontSize: 16, fontFamily: fonts.semiBold, color: colors.text },

  // Plan
  planBadge: { backgroundColor: colors.surfaceLight, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 4 },
  premiumBadge: { backgroundColor: colors.accentMuted },
  planBadgeText: { fontSize: 11, fontFamily: fonts.semiBold, color: colors.textSecondary, letterSpacing: 1 },
  premiumBadgeText: { color: colors.accent },
  expiresText: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, marginBottom: 16 },

  statsRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.bg, borderRadius: radius.md, padding: 16, marginBottom: 12 },
  statItem: { flex: 1, alignItems: 'center' },
  statValue: { fontSize: 20, fontFamily: fonts.semiBold, color: colors.text },
  statLabel: { fontSize: 11, fontFamily: fonts.regular, color: colors.textMuted, marginTop: 2 },
  statDivider: { width: 1, height: 28, backgroundColor: colors.border },
  scansSubtext: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, textAlign: 'center', marginBottom: 12 },

  cancelSubBtn: { alignItems: 'center', paddingVertical: 12 },
  cancelSubBtnText: { color: colors.error, fontSize: 14, fontFamily: fonts.regular },

  upgradeBtns: { gap: 8 },
  upgradeBtn: { alignItems: 'center', justifyContent: 'center', borderRadius: radius.md, height: 48, borderWidth: 1, borderColor: colors.border },
  upgradeBtnPrimary: { backgroundColor: colors.accent, borderColor: colors.accent },
  upgradeBtnText: { color: colors.textSecondary, fontSize: 14, fontFamily: fonts.semiBold },
  upgradeBtnPrimaryText: { color: colors.bg },

  // Referral
  referralDesc: { fontSize: 14, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 20, marginBottom: 16 },
  referralCodeRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  referralCodeBox: { flex: 1, backgroundColor: colors.bg, borderRadius: radius.sm, padding: 12, borderWidth: 1, borderColor: colors.border },
  referralCode: { fontSize: 18, fontFamily: fonts.semiBold, color: colors.text, textAlign: 'center', letterSpacing: 3 },
  iconBtn: { width: 44, height: 44, borderRadius: radius.sm, backgroundColor: colors.accentMuted, alignItems: 'center', justifyContent: 'center' },
  referralStats: { flexDirection: 'row', gap: 8, marginBottom: 16, alignItems: 'center' },
  referralStatText: { fontSize: 13, fontFamily: fonts.regular, color: colors.textMuted },
  referralStatDot: { fontSize: 13, color: colors.textMuted },
  applyRow: { flexDirection: 'row', gap: 8 },
  applyInput: { flex: 1, backgroundColor: colors.bg, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, height: 46, color: colors.text, fontSize: 14, fontFamily: fonts.regular },
  applyBtn: { backgroundColor: colors.accent, borderRadius: radius.sm, paddingHorizontal: 20, height: 46, alignItems: 'center', justifyContent: 'center' },
  applyBtnText: { color: colors.bg, fontSize: 14, fontFamily: fonts.semiBold },

  // Actions
  actionsSection: { marginTop: 8, gap: 4 },
  actionBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14 },
  actionBtnText: { fontSize: 15, fontFamily: fonts.regular },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },
  modalCard: { backgroundColor: colors.surface, borderRadius: radius.xl, padding: 28, width: '100%' },
  modalTitle: { fontSize: 18, fontFamily: fonts.semiBold, color: colors.text, marginBottom: 8 },
  modalDesc: { fontSize: 15, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 22, marginBottom: 24 },
  modalBtns: { flexDirection: 'row', gap: 12 },
  keepBtn: { flex: 1, backgroundColor: colors.accent, borderRadius: radius.md, height: 48, alignItems: 'center', justifyContent: 'center' },
  keepBtnText: { color: colors.bg, fontSize: 15, fontFamily: fonts.semiBold },
  confirmCancelBtn: { flex: 1, backgroundColor: colors.errorBg, borderWidth: 1, borderColor: colors.errorBorder, borderRadius: radius.md, height: 48, alignItems: 'center', justifyContent: 'center' },
  confirmCancelText: { color: colors.error, fontSize: 15, fontFamily: fonts.semiBold },
});
