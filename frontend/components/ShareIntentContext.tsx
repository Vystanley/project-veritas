import React, { createContext, useContext, useState, useCallback } from 'react';

interface ShareIntentContextType {
  sharedUrl: string | null;
  setSharedUrl: (url: string | null) => void;
  clearSharedUrl: () => void;
}

const ShareIntentContext = createContext<ShareIntentContextType>({
  sharedUrl: null,
  setSharedUrl: () => {},
  clearSharedUrl: () => {},
});

export function ShareIntentProvider({ children }: { children: React.ReactNode }) {
  const [sharedUrl, setSharedUrl] = useState<string | null>(null);

  const clearSharedUrl = useCallback(() => {
    setSharedUrl(null);
  }, []);

  return (
    <ShareIntentContext.Provider value={{ sharedUrl, setSharedUrl, clearSharedUrl }}>
      {children}
    </ShareIntentContext.Provider>
  );
}

export function useSharedUrl() {
  return useContext(ShareIntentContext);
}

/**
 * Extract a URL from shared data (text or webUrl).
 * Platforms like TikTok share text like: "Check out this video! https://vt.tiktok.com/..."
 * We need to extract just the URL.
 */
export function extractUrlFromShareData(shareData: { webUrl?: string; text?: string }): string | null {
  // Prefer the extracted webUrl
  if (shareData.webUrl && /^https?:\/\//i.test(shareData.webUrl)) {
    return shareData.webUrl;
  }

  // Fallback: extract URL from text
  if (shareData.text) {
    const urlMatch = shareData.text.match(/https?:\/\/[^\s]+/);
    if (urlMatch) return urlMatch[0];
  }

  return null;
}

/**
 * Detect which platform a URL is from (for displaying in the banner).
 */
export function detectPlatform(url: string): string | null {
  const lower = url.toLowerCase();
  if (lower.includes('tiktok.com') || lower.includes('vt.tiktok.com') || lower.includes('vm.tiktok.com')) return 'TikTok';
  if (lower.includes('instagram.com')) return 'Instagram';
  if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'YouTube';
  if (lower.includes('facebook.com') || lower.includes('fb.watch')) return 'Facebook';
  if (lower.includes('twitter.com') || lower.includes('x.com')) return 'Twitter/X';
  if (lower.includes('linkedin.com')) return 'LinkedIn';
  return null;
}
