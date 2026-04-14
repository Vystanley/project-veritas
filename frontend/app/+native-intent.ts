/**
 * Native intent handler for Expo Router.
 * Redirects share intent deep links to the home screen where
 * the useShareIntent hook will pick up the shared data.
 */
export async function redirectSystemPath({
  path,
  initial,
}: {
  path: string;
  initial: boolean;
}) {
  try {
    // expo-share-intent uses these paths for shared content
    if (
      path.includes('sharekey') ||
      path.includes('ShareMedia') ||
      path.includes('expo-sharing')
    ) {
      return '/home';
    }

    // Check for URL hostname-based share intents
    try {
      const url = new URL(path);
      if (url.hostname === 'expo-sharing' || url.hostname === 'share-intent') {
        return '/home';
      }
    } catch {
      // Not a valid URL, continue with normal path
    }

    return path;
  } catch {
    return '/';
  }
}
