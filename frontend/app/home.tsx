import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, Keyboard,
  ScrollView, Alert, Modal, Linking, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import { useAuth } from '../components/AuthContext';
import { useSharedUrl, detectPlatform } from '../components/ShareIntentContext';
import { colors, fonts, radius, spacing } from '../constants/theme';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// ============ SAFE FETCH WRAPPER ============

interface SafeResult {
  ok: boolean;
  status: number;
  data: any;
  error: string | null;
}

async function safeFetch(url: string, options: RequestInit = {}): Promise<SafeResult> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });

    const contentType = response.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
      const data = await response.json();
      if (response.ok || response.status === 202) {
        return { ok: true, status: response.status, data, error: null };
      }
      return { ok: false, status: response.status, data: null, error: data.detail || data.message || 'Request failed' };
    }

    // NOT JSON — proxy/load-balancer returned raw text
    if (response.status === 502 || response.status === 504) {
      return { ok: false, status: response.status, data: null, error: 'Server temporarily unavailable. Please try again in a moment.' };
    }
    return { ok: false, status: response.status, data: null, error: `Server error (${response.status}). Please try again.` };
  } catch (e: any) {
    if (e.name === 'AbortError') {
      return { ok: false, status: 0, data: null, error: 'Request timed out. Please try again.' };
    }
    return { ok: false, status: 0, data: null, error: 'Unable to connect. Check your internet connection.' };
  }
}

// ============ URL VALIDATION ============

interface UrlValidation {
  isValid: boolean;
  error: string | null;
}

function validateUrl(url: string): UrlValidation {
  const trimmed = url.trim();
  if (!trimmed) return { isValid: false, error: null };
  if (!/^https?:\/\//i.test(trimmed)) {
    return { isValid: false, error: 'Enter a valid URL starting with https://' };
  }
  const supported = [
    'tiktok.com', 'vt.tiktok.com', 'vm.tiktok.com',
    'instagram.com', 'youtube.com', 'youtu.be',
    'facebook.com', 'fb.watch',
    'twitter.com', 'x.com',
    'linkedin.com',
  ];
  if (!supported.some(domain => trimmed.toLowerCase().includes(domain))) {
    return { isValid: false, error: 'Unsupported platform. Try TikTok, Instagram, YouTube, Facebook, Twitter/X, or LinkedIn.' };
  }
  return { isValid: true, error: null };
}

// ============ TYPES ============

interface SubStatus {
  plan: string;
  scans_used: number;
  scans_remaining: number;
  is_premium: boolean;
  expires_at: string | null;
  period_resets_at: string;
  bonus_scans: number;
}

// ============ MAIN SCREEN ============

export default function HomeScreen() {
  const [url, setUrl] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [subStatus, setSubStatus] = useState<SubStatus | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const { user, token, logout, loading } = useAuth();
  const { sharedUrl, clearSharedUrl } = useSharedUrl();
  const router = useRouter();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Guards against double-navigation: several in-flight polls can all see status==='completed'
  // before clearInterval takes effect, which would push the Results screen multiple times.
  const navigatedRef = useRef(false);

  // Share intent banner
  const [showBanner, setShowBanner] = useState(false);
  const [bannerPlatform, setBannerPlatform] = useState<string | null>(null);
  const bannerOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!loading && !user) router.replace('/');
    if (!loading && user && !user.email_verified) router.replace('/verify-email');
  }, [user, loading]);

  useEffect(() => {
    if (token) fetchSubscription();
  }, [token]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  // Consume shared URL from share intent
  useEffect(() => {
    if (sharedUrl && !isProcessing) {
      setUrl(sharedUrl);
      const platform = detectPlatform(sharedUrl);
      setBannerPlatform(platform);
      setShowBanner(true);
      clearSharedUrl();

      // Animate banner in, then auto-dismiss after 3 seconds
      Animated.timing(bannerOpacity, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start(() => {
        setTimeout(() => {
          Animated.timing(bannerOpacity, {
            toValue: 0,
            duration: 500,
            useNativeDriver: true,
          }).start(() => setShowBanner(false));
        }, 3000);
      });
    }
  }, [sharedUrl]);

  const fetchSubscription = useCallback(async () => {
    const res = await safeFetch(`${BACKEND_URL}/api/subscription/status`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setSubStatus(res.data);
  }, [token]);

  if (loading || !user) {
    return <View style={styles.loadingContainer}><ActivityIndicator size="large" color={colors.accent} /></View>;
  }

  async function handlePaste() {
    try {
      const text = await Clipboard.getStringAsync();
      if (text) setUrl(text);
    } catch {}
  }

  async function handleUpgrade(plan: string) {
    setUpgrading(true);
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : BACKEND_URL;
      const res = await safeFetch(`${BACKEND_URL}/api/payments/checkout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ plan, origin_url: origin }),
      });
      if (!res.ok) throw new Error(res.error || 'Checkout failed');
      const checkoutUrl = res.data.url;
      if (Platform.OS === 'web') {
        setShowUpgrade(false);
        window.location.href = checkoutUrl;
      } else {
        await Linking.openURL(checkoutUrl);
        setShowUpgrade(false);
        fetchSubscription();
      }
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Checkout failed');
    } finally {
      setUpgrading(false);
    }
  }

  const validation = validateUrl(url);
  const hasUrl = url.trim().length > 0;

  // ============ VERIFY (SUBMIT → POLL) ============

  async function handleVerify() {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) { Alert.alert('Missing URL', 'Please paste a video URL to analyze'); return; }
    if (!validation.isValid) { Alert.alert('Invalid URL', validation.error || 'Please enter a valid URL'); return; }

    Keyboard.dismiss();
    setIsProcessing(true);
    setProgress(0);
    setProgressMessage('Submitting...');

    // Step 1: Submit the job
    const submitResult = await safeFetch(`${BACKEND_URL}/api/fact-check`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ video_url: trimmedUrl }),
    });

    if (!submitResult.ok) {
      setIsProcessing(false);
      setProgress(0);
      setProgressMessage('');
      if (submitResult.status === 429) {
        Alert.alert('Scan Limit Reached', submitResult.error || 'Upgrade to Premium for more scans.', [
          { text: 'Later', style: 'cancel' },
          { text: 'Upgrade', onPress: () => setShowUpgrade(true) },
        ]);
      } else {
        Alert.alert('Error', submitResult.error || 'Could not start analysis. Please try again.');
      }
      return;
    }

    const jobId = submitResult.data.job_id;
    setProgress(5);
    setProgressMessage('Processing started...');
    navigatedRef.current = false;

    // Step 2: Poll for results every 3 seconds
    pollRef.current = setInterval(async () => {
      const statusResult = await safeFetch(`${BACKEND_URL}/api/fact-check/${jobId}/status`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!statusResult.ok) return; // Retry on next poll

      const { status, progress: prog, progress_message, result, error } = statusResult.data;

      setProgress(prog);
      setProgressMessage(progress_message);

      if (status === 'completed' && result) {
        if (navigatedRef.current) return; // Another in-flight poll already handled this
        navigatedRef.current = true;
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
        setIsProcessing(false);
        setProgress(0);
        setProgressMessage('');
        fetchSubscription();
        router.push({ pathname: '/results', params: { data: JSON.stringify(result) } });
        return;
      }

      if (status === 'failed') {
        if (navigatedRef.current) return;
        navigatedRef.current = true;
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
        setIsProcessing(false);
        setProgress(0);
        setProgressMessage('');
        Alert.alert('Analysis Failed', error || 'Could not analyze the video. Please try again.');
      }
    }, 3000);

    // Safety timeout: stop polling after 4 minutes
    timeoutRef.current = setTimeout(() => {
      if (pollRef.current) clearInterval(pollRef.current);
      setIsProcessing(false);
      setProgress(0);
      setProgressMessage('');
      Alert.alert('Timeout', 'Analysis is taking too long. Please try a shorter video or try again later.');
    }, 240000);
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.brandName}>VERITAS</Text>
            <TouchableOpacity testID="settings-btn" style={styles.settingsBtn} onPress={() => router.push('/settings')}>
              <Ionicons name="settings-outline" size={20} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>

          {/* Share Intent Banner */}
          {showBanner && (
            <Animated.View style={[styles.shareBanner, { opacity: bannerOpacity }]}>
              <Ionicons name="share-outline" size={16} color={colors.accent} />
              <Text style={styles.shareBannerText}>
                URL received{bannerPlatform ? ` from ${bannerPlatform}` : ''} — ready to verify
              </Text>
            </Animated.View>
          )}

          {/* Main Content */}
          <View style={styles.mainContent}>
            {/* Scan Counter & Upgrade Prompt */}
            {subStatus && !isProcessing && (
              <View style={styles.scanInfoBar}>
                <View style={styles.scanCountWrap}>
                  <View style={[styles.scanDot, subStatus.scans_remaining > 0 ? styles.scanDotActive : styles.scanDotEmpty]} />
                  <Text style={styles.scanCountText}>
                    {subStatus.is_premium
                      ? `${subStatus.scans_remaining} scans left`
                      : `${subStatus.scans_remaining} free scan${subStatus.scans_remaining !== 1 ? 's' : ''} left`}
                  </Text>
                </View>
                {!subStatus.is_premium && (
                  <TouchableOpacity testID="home-upgrade-btn" style={styles.upgradeChip} onPress={() => setShowUpgrade(true)} activeOpacity={0.7}>
                    <Text style={styles.upgradeChipText}>Upgrade</Text>
                    <Ionicons name="arrow-forward" size={12} color={colors.accent} />
                  </TouchableOpacity>
                )}
                {subStatus.is_premium && (
                  <View style={styles.proBadge}>
                    <Text style={styles.proBadgeText}>PRO</Text>
                  </View>
                )}
              </View>
            )}

            <Text style={styles.heroTitle}>Verify{'\n'}video content</Text>
            <Text style={styles.heroSubtitle}>Paste a link from TikTok, Instagram, YouTube or any platform</Text>

            {/* URL Input */}
            <View style={styles.inputSection}>
              <View style={[
                styles.urlInputWrapper,
                hasUrl && !validation.isValid && validation.error ? styles.urlInputInvalid : null,
                validation.isValid ? styles.urlInputValid : null,
              ]}>
                <Ionicons
                  name="link-outline"
                  size={18}
                  color={hasUrl && !validation.isValid && validation.error ? colors.error : validation.isValid ? colors.accent : colors.textMuted}
                  style={styles.urlIcon}
                />
                <TextInput
                  testID="video-url-input"
                  style={styles.urlInput}
                  placeholder="https://..."
                  placeholderTextColor={colors.textMuted}
                  value={url}
                  onChangeText={setUrl}
                  autoCapitalize="none"
                  autoCorrect={false}
                  editable={!isProcessing}
                />
                {!hasUrl && (
                  <TouchableOpacity testID="paste-url-btn" style={styles.pasteBtn} onPress={handlePaste} disabled={isProcessing}>
                    <Ionicons name="clipboard-outline" size={16} color={colors.accent} />
                    <Text style={styles.pasteBtnText}>Paste</Text>
                  </TouchableOpacity>
                )}
                {hasUrl && !isProcessing && (
                  <TouchableOpacity style={styles.clearBtn} onPress={() => setUrl('')}>
                    <Ionicons name="close-circle" size={18} color={colors.textMuted} />
                  </TouchableOpacity>
                )}
              </View>
              {hasUrl && !validation.isValid && validation.error && (
                <Text style={styles.urlError} testID="url-validation-error">{validation.error}</Text>
              )}

              {/* Progress Bar */}
              {isProcessing && (
                <View style={styles.progressSection}>
                  <View style={styles.progressBarBg}>
                    <View style={[styles.progressBarFill, { width: `${Math.max(progress, 3)}%` }]} />
                  </View>
                  <View style={styles.progressInfo}>
                    <Text style={styles.progressText}>{progressMessage || 'Processing...'}</Text>
                    <Text style={styles.progressPercent}>{progress}%</Text>
                  </View>
                </View>
              )}

              <TouchableOpacity
                testID="analyze-btn"
                style={[styles.verifyBtn, (!validation.isValid || isProcessing) && styles.verifyBtnDisabled]}
                onPress={handleVerify}
                disabled={!validation.isValid || isProcessing}
                activeOpacity={0.8}
              >
                {isProcessing ? (
                  <View style={styles.analyzingContent}>
                    <ActivityIndicator color={colors.bg} size="small" />
                    <Text style={styles.verifyBtnText}>Analyzing...</Text>
                  </View>
                ) : (
                  <Text style={styles.verifyBtnText}>Verify</Text>
                )}
              </TouchableOpacity>
            </View>

            {/* Supported platforms as subtle text */}
            {!isProcessing && (
              <Text style={styles.platformsText}>
                Works with TikTok, Instagram Reels, YouTube Shorts, Facebook, LinkedIn, and Twitter/X
              </Text>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Upgrade Modal */}
      <Modal visible={showUpgrade} animationType="slide" transparent>
        <View style={m.overlay}>
          <View style={m.sheet}>
            <View style={m.handle} />
            <TouchableOpacity testID="close-upgrade-modal" style={m.closeBtn} onPress={() => setShowUpgrade(false)}>
              <Ionicons name="close" size={24} color={colors.textSecondary} />
            </TouchableOpacity>
            <View style={m.header}>
              <Text style={m.title}>Upgrade to Premium</Text>
              <Text style={m.subtitle}>Unlimited fact-checks to verify any video</Text>
            </View>
            <View style={m.features}>
              {['Unlimited video scans', 'Priority processing', 'Detailed source references', 'Ad-free experience'].map((f, i) => (
                <View key={i} style={m.featureRow}>
                  <Ionicons name="checkmark" size={16} color={colors.accent} />
                  <Text style={m.featureText}>{f}</Text>
                </View>
              ))}
            </View>
            <TouchableOpacity testID="plan-monthly-btn" style={m.planCard} onPress={() => handleUpgrade('premium_monthly')} disabled={upgrading} activeOpacity={0.8}>
              <View style={m.planInfo}>
                <Text style={m.planName}>Monthly</Text>
                <Text style={m.planPrice}>$13.99<Text style={m.planPeriod}>/month</Text></Text>
              </View>
              {upgrading ? <ActivityIndicator color={colors.accent} /> : <Ionicons name="arrow-forward" size={20} color={colors.accent} />}
            </TouchableOpacity>
            <TouchableOpacity testID="plan-annual-btn" style={[m.planCard, m.planCardBest]} onPress={() => handleUpgrade('premium_annual')} disabled={upgrading} activeOpacity={0.8}>
              <View style={m.bestBadge}><Text style={m.bestBadgeText}>BEST VALUE</Text></View>
              <View style={m.planInfo}>
                <Text style={m.planName}>Annual</Text>
                <Text style={m.planPrice}>$119<Text style={m.planPeriod}>/year</Text></Text>
                <Text style={m.planSave}>Save 29%</Text>
              </View>
              {upgrading ? <ActivityIndicator color={colors.accent} /> : <Ionicons name="arrow-forward" size={20} color={colors.accent} />}
            </TouchableOpacity>
            <Text style={m.fineprint}>Powered by Stripe. Cancel anytime.</Text>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// ============ STYLES ============

const m = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingHorizontal: 24, paddingBottom: 40, paddingTop: 16 },
  handle: { width: 36, height: 4, borderRadius: 2, backgroundColor: colors.borderLight, alignSelf: 'center', marginBottom: 20 },
  closeBtn: { position: 'absolute', top: 16, right: 20, zIndex: 10, width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  header: { marginBottom: 24 },
  title: { fontSize: 22, fontFamily: fonts.semiBold, color: colors.text, marginBottom: 6 },
  subtitle: { fontSize: 15, fontFamily: fonts.regular, color: colors.textSecondary },
  features: { marginBottom: 28, gap: 14 },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  featureText: { fontSize: 15, fontFamily: fonts.regular, color: colors.text },
  planCard: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.surfaceLight, borderRadius: radius.lg, padding: 20, marginBottom: 12, borderWidth: 1, borderColor: colors.border },
  planCardBest: { borderColor: colors.accent },
  bestBadge: { position: 'absolute', top: -10, right: 16, backgroundColor: colors.accent, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 3 },
  bestBadgeText: { fontSize: 10, fontFamily: fonts.semiBold, color: colors.bg, letterSpacing: 0.5 },
  planInfo: { flex: 1 },
  planName: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, marginBottom: 2 },
  planPrice: { fontSize: 24, fontFamily: fonts.semiBold, color: colors.text },
  planPeriod: { fontSize: 14, fontFamily: fonts.regular, color: colors.textSecondary },
  planSave: { fontSize: 13, fontFamily: fonts.semiBold, color: colors.accent, marginTop: 2 },
  fineprint: { fontSize: 12, fontFamily: fonts.regular, color: colors.textMuted, textAlign: 'center', marginTop: 16 },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  loadingContainer: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
  scrollContent: { flexGrow: 1, paddingHorizontal: 24 },

  // Header
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 8, marginBottom: 0 },
  brandName: { fontSize: 16, fontFamily: fonts.semiBold, color: colors.textSecondary, letterSpacing: 4 },
  settingsBtn: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },

  // Share Intent Banner
  shareBanner: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: colors.accentMuted, borderRadius: radius.sm, paddingHorizontal: 14, paddingVertical: 10, marginTop: 8, borderWidth: 1, borderColor: colors.accentBorder },
  shareBannerText: { fontSize: 13, fontFamily: fonts.semiBold, color: colors.accent, flex: 1 },

  // Main Content
  mainContent: { flex: 1, justifyContent: 'center', paddingBottom: 40 },

  // Scan Info Bar
  scanInfoBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, paddingVertical: 10, marginBottom: 24 },
  scanCountWrap: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  scanDot: { width: 8, height: 8, borderRadius: 4 },
  scanDotActive: { backgroundColor: colors.accent },
  scanDotEmpty: { backgroundColor: colors.error },
  scanCountText: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary },
  upgradeChip: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: colors.accentMuted, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6 },
  upgradeChipText: { fontSize: 13, fontFamily: fonts.semiBold, color: colors.accent },
  proBadge: { backgroundColor: colors.accentMuted, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 4 },
  proBadgeText: { fontSize: 11, fontFamily: fonts.semiBold, color: colors.accent, letterSpacing: 1 },

  heroTitle: { fontSize: 36, fontFamily: fonts.semiBold, color: colors.text, lineHeight: 44, marginBottom: 12 },
  heroSubtitle: { fontSize: 16, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 24, marginBottom: 36 },

  // Input
  inputSection: { marginBottom: 24 },
  urlInputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 16, height: 56, marginBottom: 6 },
  urlInputInvalid: { borderColor: colors.error },
  urlInputValid: { borderColor: colors.accentBorder },
  urlError: { color: colors.error, fontSize: 12, fontFamily: fonts.regular, marginBottom: 8, marginLeft: 4 },
  urlIcon: { marginRight: 10 },
  urlInput: { flex: 1, color: colors.text, fontSize: 15, fontFamily: fonts.regular, height: '100%' },
  pasteBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.sm, backgroundColor: colors.accentMuted },
  pasteBtnText: { color: colors.accent, fontSize: 13, fontFamily: fonts.semiBold },
  clearBtn: { padding: 4 },

  // Progress Bar
  progressSection: { marginBottom: 12, marginTop: 4 },
  progressBarBg: { height: 6, backgroundColor: colors.surfaceLight, borderRadius: 3, overflow: 'hidden' },
  progressBarFill: { height: '100%', backgroundColor: colors.accent, borderRadius: 3 },
  progressInfo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 },
  progressText: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, flex: 1 },
  progressPercent: { fontSize: 13, fontFamily: fonts.semiBold, color: colors.accent },

  // Verify Button
  verifyBtn: { backgroundColor: colors.accent, borderRadius: radius.md, height: 56, alignItems: 'center', justifyContent: 'center', marginTop: 6 },
  verifyBtnDisabled: { backgroundColor: colors.surfaceLight },
  analyzingContent: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  verifyBtnText: { color: colors.bg, fontSize: 17, fontFamily: fonts.semiBold },

  // Platforms
  platformsText: { fontSize: 14, fontFamily: fonts.regular, color: colors.textMuted, textAlign: 'center', lineHeight: 22, marginTop: 16 },
});
