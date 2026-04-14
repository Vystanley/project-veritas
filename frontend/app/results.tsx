import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  Alert, Share, Platform, ActivityIndicator, Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors, fonts, radius } from '../constants/theme';

interface ClaimItem {
  claim: string;
  verdict: string;
  explanation: string;
  sources: string[];
}

interface SourceItem {
  title: string;
  url: string;
  description: string;
}

interface DeepfakeData {
  is_deepfake: boolean;
  confidence: number;
  risk_level: string;
  analysis: string;
  indicators: string[];
}

interface ReverseImageMatch {
  title: string;
  url: string;
  source: string;
  date: string;
  thumbnail: string;
}

interface ReverseImageData {
  enabled: boolean;
  frame_url?: string | null;
  matches: ReverseImageMatch[];
  earliest_date?: string | null;
  note: string;
}

interface FactCheckData {
  id: string;
  overall_verdict: string;
  confidence_score: number;
  summary: string;
  transcript: string;
  visual_description?: string | null;
  claims: ClaimItem[];
  sources: SourceItem[];
  deepfake: DeepfakeData;
  reverse_image?: ReverseImageData | null;
  video_url: string;
  created_at: string;
}

function getVerdictColor(verdict: string): string {
  const v = verdict.toLowerCase();
  if (v === 'false') return '#E74C3C';
  if (v.includes('mostly false')) return '#E67E22';
  if (v.includes('partially')) return '#F59E0B';
  if (v.includes('mostly true')) return '#8BC34A';
  if (v === 'true') return '#4CAF50';
  return colors.textSecondary;
}

function getVerdictIcon(verdict: string): string {
  const v = verdict.toLowerCase();
  if (v === 'false') return 'close-circle';
  if (v.includes('mostly false')) return 'close-circle-outline';
  if (v.includes('partially')) return 'alert-circle';
  if (v.includes('mostly true')) return 'checkmark-circle-outline';
  if (v === 'true') return 'checkmark-circle';
  return 'help-circle';
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#4CAF50';
  if (score >= 60) return '#8BC34A';
  if (score >= 40) return '#F59E0B';
  if (score >= 20) return '#E67E22';
  return '#E74C3C';
}

function getDeepfakeColor(risk: string): string {
  if (risk === 'high') return '#E74C3C';
  if (risk === 'medium') return '#F59E0B';
  if (risk === 'low') return '#4CAF50';
  return colors.textSecondary;
}

function getDeepfakeIcon(risk: string): string {
  if (risk === 'high') return 'warning';
  if (risk === 'medium') return 'alert-circle';
  if (risk === 'low') return 'shield-checkmark';
  return 'help-circle';
}

const URL_REGEX = /https?:\/\/[^\s,)>\]]+/gi;

function openUrl(url: string) {
  Linking.openURL(url).catch(() => {
    Alert.alert('Error', 'Could not open this link');
  });
}

function TextWithLinks({ text, style }: { text: string; style?: any }) {
  const parts = text.split(URL_REGEX);
  const matches = text.match(URL_REGEX) || [];

  if (matches.length === 0) {
    return <Text style={style}>{text}</Text>;
  }

  const elements: React.ReactNode[] = [];
  parts.forEach((part, i) => {
    if (part) elements.push(<Text key={`t${i}`} style={style}>{part}</Text>);
    if (i < matches.length) {
      elements.push(
        <Text
          key={`l${i}`}
          style={[style, { color: colors.accent, textDecorationLine: 'underline' }]}
          onPress={() => openUrl(matches[i])}
          data-testid={`link-${i}`}
        >
          {matches[i]}
        </Text>
      );
    }
  });
  return <Text>{elements}</Text>;
}

export default function ResultsScreen() {
  const router = useRouter();
  const { data: dataStr } = useLocalSearchParams<{ data: string }>();
  const [sharing, setSharing] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showVisual, setShowVisual] = useState(false);
  const [showReverseImage, setShowReverseImage] = useState(false);

  let result: FactCheckData | null = null;
  try {
    result = dataStr ? JSON.parse(dataStr) : null;
  } catch {
    result = null;
  }

  if (!result) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorWrap}>
          <Ionicons name="alert-circle" size={48} color={colors.error} />
          <Text style={styles.errorText}>No results found</Text>
          <TouchableOpacity data-testid="back-home-btn" style={styles.backBtn} onPress={() => router.back()}>
            <Text style={styles.backBtnText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const verdictColor = getVerdictColor(result.overall_verdict);
  const scoreColor = getScoreColor(result.confidence_score);
  const deepfake = result.deepfake;
  const dfColor = getDeepfakeColor(deepfake?.risk_level || 'unknown');
  const dfIcon = getDeepfakeIcon(deepfake?.risk_level || 'unknown');

  async function handleShare() {
    setSharing(true);
    try {
      const verdict = result!.overall_verdict;
      const confidence = result!.confidence_score;
      const videoUrl = result!.video_url;
      const summary = result!.summary || '';

      const shareText = `🔍 I fact-checked this video with Veritas:\n\n` +
        `📹 ${videoUrl}\n\n` +
        `Verdict: ${verdict}\n` +
        `Confidence: ${confidence}%\n\n` +
        `${summary}\n\n` +
        `Download Veritas to fact-check videos yourself!`;

      await Share.share({
        message: shareText,
        ...(Platform.OS === 'ios' ? { url: videoUrl } : {}),
      });
    } catch (e: any) {
      if (e.message !== 'User cancelled') {
        Alert.alert('Share Failed', 'Could not share the results');
      }
    } finally {
      setSharing(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity data-testid="results-back-btn" style={styles.headerBackBtn} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={20} color={colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Results</Text>
          <TouchableOpacity data-testid="share-btn" style={styles.shareHeaderBtn} onPress={handleShare} disabled={sharing}>
            {sharing ? (
              <ActivityIndicator size={16} color={colors.accent} />
            ) : (
              <Ionicons name="share-outline" size={20} color={colors.accent} />
            )}
          </TouchableOpacity>
        </View>

        {/* Verdict Card */}
        <View style={[styles.verdictCard, { borderColor: verdictColor }]}>
          <View style={styles.verdictTop}>
            <View style={[styles.verdictIconWrap, { backgroundColor: `${verdictColor}15` }]}>
              <Ionicons name={getVerdictIcon(result.overall_verdict) as any} size={36} color={verdictColor} />
            </View>
            <View style={styles.verdictTextWrap}>
              <Text style={styles.verdictLabel}>Overall Verdict</Text>
              <Text style={[styles.verdictText, { color: verdictColor }]}>
                {result.overall_verdict}
              </Text>
            </View>
          </View>

          {/* Confidence Score */}
          <View style={styles.scoreSection}>
            <View style={styles.scoreRow}>
              <Text style={styles.scoreTitle}>AI Confidence</Text>
              <Text style={[styles.scoreValue, { color: scoreColor }]}>{result.confidence_score}%</Text>
            </View>
            <View style={styles.scoreBarBg}>
              <View style={[styles.scoreBarFill, { width: `${result.confidence_score}%`, backgroundColor: scoreColor }]} />
            </View>
          </View>

          {/* Summary */}
          <TextWithLinks text={result.summary} style={styles.summary} />
        </View>

        {/* Deepfake Analysis Card */}
        {deepfake && (
          <View style={[styles.sectionCard, { borderColor: dfColor }]} data-testid="deepfake-card">
            <View style={styles.sectionHeader}>
              <Ionicons name={dfIcon as any} size={20} color={dfColor} />
              <Text style={styles.sectionTitle}>Deepfake Analysis</Text>
              <View style={[styles.dfBadge, { backgroundColor: `${dfColor}18`, borderColor: `${dfColor}40` }]}>
                <Text style={[styles.dfBadgeText, { color: dfColor }]}>
                  {deepfake.risk_level === 'unknown' ? 'SKIPPED' : deepfake.risk_level.toUpperCase()}
                </Text>
              </View>
            </View>

            {deepfake.risk_level !== 'unknown' && deepfake.confidence > 0 && (
              <View style={styles.dfScoreRow}>
                <Text style={styles.dfScoreLabel}>Detection Confidence</Text>
                <Text style={[styles.dfScoreValue, { color: dfColor }]}>{deepfake.confidence}%</Text>
              </View>
            )}

            <Text style={styles.dfAnalysis}>{deepfake.analysis}</Text>

            {deepfake.indicators && deepfake.indicators.length > 0 && (
              <View style={styles.dfIndicators}>
                {deepfake.indicators.map((ind, i) => (
                  <View key={i} style={styles.dfIndicatorRow}>
                    <View style={[styles.dfDot, { backgroundColor: dfColor }]} />
                    <Text style={styles.dfIndicatorText}>{ind}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* Claims Section */}
        {result.claims && result.claims.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons name="list-circle" size={20} color={colors.accent} />
              <Text style={styles.sectionTitle}>Claims Analysis</Text>
              <View style={styles.claimCountBadge}>
                <Text style={styles.claimCountText}>{result.claims.length}</Text>
              </View>
            </View>

            {result.claims.map((claim, index) => {
              const claimColor = getVerdictColor(claim.verdict);
              return (
                <View key={index} style={[styles.claimCard, { borderLeftColor: claimColor }]} data-testid={`claim-card-${index}`}>
                  <View style={styles.claimHeader}>
                    <Ionicons name={getVerdictIcon(claim.verdict) as any} size={16} color={claimColor} />
                    <Text style={[styles.claimVerdict, { color: claimColor }]}>{claim.verdict}</Text>
                  </View>
                  <Text style={styles.claimText}>{claim.claim}</Text>
                  <TextWithLinks text={claim.explanation} style={styles.claimExplanation} />
                  {claim.sources && claim.sources.length > 0 && (
                    <View style={styles.claimSources}>
                      {claim.sources.map((src, si) => {
                        const isUrl = /^https?:\/\//i.test(src);
                        return (
                          <TouchableOpacity
                            key={si}
                            style={styles.claimSourceTag}
                            onPress={() => isUrl ? openUrl(src) : null}
                            disabled={!isUrl}
                            data-testid={`claim-source-${index}-${si}`}
                          >
                            <Ionicons name={isUrl ? 'open-outline' : 'link-outline'} size={11} color={colors.accent} />
                            <Text style={[styles.claimSourceText, isUrl && { textDecorationLine: 'underline' }]} numberOfLines={1}>
                              {src}
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  )}
                </View>
              );
            })}
          </View>
        )}

        {/* Sources / References Section */}
        {result.sources && result.sources.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons name="document-text-outline" size={20} color={colors.accent} />
              <Text style={styles.sectionTitle}>References</Text>
            </View>
            {result.sources.map((source, index) => {
              const hasUrl = !!source.url && /^https?:\/\//i.test(source.url);
              return (
                <TouchableOpacity
                  key={index}
                  style={styles.sourceCard}
                  onPress={() => hasUrl ? openUrl(source.url) : null}
                  disabled={!hasUrl}
                  activeOpacity={hasUrl ? 0.7 : 1}
                  data-testid={`source-card-${index}`}
                >
                  <View style={styles.sourceInfo}>
                    <Text style={[styles.sourceTitle, hasUrl && { color: colors.accent }]}>{source.title}</Text>
                    {source.description ? (
                      <Text style={styles.sourceDesc} numberOfLines={2}>{source.description}</Text>
                    ) : null}
                    {source.url ? (
                      <Text style={[styles.sourceUrl, hasUrl && { textDecorationLine: 'underline' }]} numberOfLines={1}>
                        {source.url}
                      </Text>
                    ) : null}
                  </View>
                  {hasUrl && <Ionicons name="open-outline" size={14} color={colors.textMuted} />}
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {/* Visual Analysis Section (Collapsible) — what the AI saw on screen */}
        {result.visual_description && result.visual_description.trim().length > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              data-testid="toggle-visual-btn"
              style={styles.sectionHeaderToggle}
              onPress={() => setShowVisual(!showVisual)}
              activeOpacity={0.7}
            >
              <View style={styles.sectionHeader}>
                <Ionicons name="eye-outline" size={20} color={colors.accent} />
                <Text style={styles.sectionTitle}>What the AI saw</Text>
              </View>
              <Ionicons name={showVisual ? 'chevron-up' : 'chevron-down'} size={18} color={colors.textMuted} />
            </TouchableOpacity>
            {showVisual && (
              <View style={styles.transcriptCard}>
                <Text style={styles.transcriptText}>{result.visual_description}</Text>
              </View>
            )}
          </View>
        )}

        {/* Reverse Image Search Section (Collapsible) */}
        {result.reverse_image && result.reverse_image.enabled && (result.reverse_image.matches?.length ?? 0) > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              data-testid="toggle-reverse-image-btn"
              style={styles.sectionHeaderToggle}
              onPress={() => setShowReverseImage(!showReverseImage)}
              activeOpacity={0.7}
            >
              <View style={styles.sectionHeader}>
                <Ionicons name="images-outline" size={20} color={colors.accent} />
                <Text style={styles.sectionTitle}>Reverse image search</Text>
                <View style={styles.claimCountBadge}>
                  <Text style={styles.claimCountText}>{result.reverse_image.matches.length}</Text>
                </View>
              </View>
              <Ionicons name={showReverseImage ? 'chevron-up' : 'chevron-down'} size={18} color={colors.textMuted} />
            </TouchableOpacity>
            {showReverseImage && (
              <View style={styles.transcriptCard}>
                {result.reverse_image.earliest_date ? (
                  <Text style={[styles.transcriptText, { marginBottom: 10 }]}>
                    Earliest appearance on the web: {result.reverse_image.earliest_date}
                  </Text>
                ) : null}
                {result.reverse_image.matches.map((m, i) => {
                  const hasUrl = !!m.url && /^https?:\/\//i.test(m.url);
                  return (
                    <TouchableOpacity
                      key={i}
                      style={[styles.sourceCard, { marginTop: i === 0 ? 0 : 8, marginBottom: 0 }]}
                      onPress={() => hasUrl ? openUrl(m.url) : null}
                      disabled={!hasUrl}
                      activeOpacity={hasUrl ? 0.7 : 1}
                      data-testid={`reverse-image-match-${i}`}
                    >
                      <View style={styles.sourceInfo}>
                        <Text style={[styles.sourceTitle, hasUrl && { color: colors.accent }]} numberOfLines={2}>
                          {m.title || m.source || m.url}
                        </Text>
                        {m.source || m.date ? (
                          <Text style={styles.sourceDesc} numberOfLines={1}>
                            {[m.source, m.date].filter(Boolean).join(' • ')}
                          </Text>
                        ) : null}
                        {m.url ? (
                          <Text style={[styles.sourceUrl, hasUrl && { textDecorationLine: 'underline' }]} numberOfLines={1}>
                            {m.url}
                          </Text>
                        ) : null}
                      </View>
                      {hasUrl && <Ionicons name="open-outline" size={14} color={colors.textMuted} />}
                    </TouchableOpacity>
                  );
                })}
              </View>
            )}
          </View>
        )}

        {/* Transcript Section (Collapsible) */}
        <View style={styles.section}>
          <TouchableOpacity
            data-testid="toggle-transcript-btn"
            style={styles.sectionHeaderToggle}
            onPress={() => setShowTranscript(!showTranscript)}
            activeOpacity={0.7}
          >
            <View style={styles.sectionHeader}>
              <Ionicons name="chatbox-ellipses-outline" size={20} color={colors.accent} />
              <Text style={styles.sectionTitle}>Transcript</Text>
            </View>
            <Ionicons name={showTranscript ? 'chevron-up' : 'chevron-down'} size={18} color={colors.textMuted} />
          </TouchableOpacity>
          {showTranscript && (
            <View style={styles.transcriptCard}>
              <Text style={styles.transcriptText}>{result.transcript}</Text>
            </View>
          )}
        </View>

        {/* Action Buttons */}
        <View style={styles.actionsRow}>
          <TouchableOpacity
            data-testid="share-results-btn"
            style={styles.shareBtn}
            onPress={handleShare}
            disabled={sharing}
            activeOpacity={0.8}
          >
            <Ionicons name="share-social-outline" size={18} color={colors.accent} />
            <Text style={styles.shareBtnText}>Share</Text>
          </TouchableOpacity>

          <TouchableOpacity
            data-testid="check-another-btn"
            style={styles.checkAnotherBtn}
            onPress={() => router.back()}
            activeOpacity={0.8}
          >
            <Text style={styles.checkAnotherText}>Check Another</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 40 },
  errorWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  errorText: { color: colors.text, fontSize: 18, fontFamily: fonts.semiBold },
  backBtn: { backgroundColor: colors.accent, borderRadius: radius.md, paddingHorizontal: 24, paddingVertical: 12 },
  backBtnText: { color: colors.bg, fontSize: 16, fontFamily: fonts.semiBold },

  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: 8, marginBottom: 20 },
  headerBackBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 17, fontFamily: fonts.semiBold, color: colors.text },
  shareHeaderBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },

  // Verdict
  verdictCard: { backgroundColor: colors.surface, borderRadius: radius.xl, borderWidth: 1, padding: 24, marginBottom: 20 },
  verdictTop: { flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 20 },
  verdictIconWrap: { width: 60, height: 60, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  verdictTextWrap: { flex: 1 },
  verdictLabel: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, marginBottom: 2 },
  verdictText: { fontSize: 24, fontFamily: fonts.semiBold },
  scoreSection: { marginBottom: 16 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  scoreTitle: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary },
  scoreValue: { fontSize: 18, fontFamily: fonts.semiBold },
  scoreBarBg: { height: 6, backgroundColor: colors.surfaceLight, borderRadius: 3, overflow: 'hidden' },
  scoreBarFill: { height: '100%', borderRadius: 3 },
  summary: { fontSize: 15, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 23 },

  // Deepfake
  sectionCard: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, padding: 20, marginBottom: 20 },
  dfBadge: { borderRadius: 6, paddingHorizontal: 10, paddingVertical: 3, borderWidth: 1 },
  dfBadgeText: { fontSize: 10, fontFamily: fonts.semiBold, letterSpacing: 0.5 },
  dfScoreRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12, marginBottom: 8 },
  dfScoreLabel: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary },
  dfScoreValue: { fontSize: 18, fontFamily: fonts.semiBold },
  dfAnalysis: { fontSize: 14, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 21, marginTop: 8 },
  dfIndicators: { marginTop: 12, gap: 6 },
  dfIndicatorRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
  dfDot: { width: 5, height: 5, borderRadius: 3, marginTop: 7 },
  dfIndicatorText: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 19, flex: 1 },

  // Sections
  section: { marginBottom: 20 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1, marginBottom: 14 },
  sectionHeaderToggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  sectionTitle: { fontSize: 16, fontFamily: fonts.semiBold, color: colors.text, flex: 1 },
  claimCountBadge: { backgroundColor: colors.accentMuted, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 3 },
  claimCountText: { color: colors.accent, fontSize: 12, fontFamily: fonts.semiBold },

  claimCard: { backgroundColor: colors.surface, borderRadius: radius.md, borderLeftWidth: 3, padding: 16, marginBottom: 10 },
  claimHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  claimVerdict: { fontSize: 12, fontFamily: fonts.semiBold, textTransform: 'uppercase', letterSpacing: 0.5 },
  claimText: { fontSize: 15, fontFamily: fonts.semiBold, color: colors.text, marginBottom: 8, lineHeight: 22 },
  claimExplanation: { fontSize: 14, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 21 },
  claimSources: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  claimSourceTag: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: colors.accentMuted, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 },
  claimSourceText: { color: colors.accent, fontSize: 11, fontFamily: fonts.regular, maxWidth: 180 },

  sourceCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: 14, marginBottom: 8, gap: 12 },
  sourceInfo: { flex: 1 },
  sourceTitle: { fontSize: 14, fontFamily: fonts.semiBold, color: colors.text, marginBottom: 3 },
  sourceDesc: { fontSize: 13, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 19 },
  sourceUrl: { fontSize: 12, fontFamily: fonts.regular, color: colors.accent, marginTop: 4 },

  transcriptCard: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: 16 },
  transcriptText: { fontSize: 14, fontFamily: fonts.regular, color: colors.textSecondary, lineHeight: 22 },

  actionsRow: { flexDirection: 'row', gap: 12 },
  shareBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, borderRadius: radius.md, height: 52, gap: 8, borderWidth: 1, borderColor: colors.border },
  shareBtnText: { color: colors.accent, fontSize: 15, fontFamily: fonts.semiBold },
  checkAnotherBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: colors.accent, borderRadius: radius.md, height: 52, gap: 8 },
  checkAnotherText: { color: colors.bg, fontSize: 15, fontFamily: fonts.semiBold },
});
