import { Link2, Loader2, AlertCircle } from "lucide-react";

interface Props {
  url: string;
  setUrl: (v: string) => void;
  onSubmit: (url: string) => void;
  loading: boolean;
  progress: number;
  progressMsg: string;
  error: string | null;
}

const EXAMPLES: { label: string; url: string }[] = [
  {
    label: "Chongqing underground city",
    url: "https://www.tiktok.com/@dylan.page/video/7456898678138146080",
  },
  {
    label: "Flat earth Antarctica",
    url: "https://www.tiktok.com/@flatearthantarctica/video/7625252294820465942",
  },
];

export function Hero({ url, setUrl, onSubmit, loading, progress, progressMsg, error }: Props) {
  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !loading) onSubmit(url);
  }

  return (
    <section className="px-4 pt-16 pb-12 sm:pt-24 sm:pb-20">
      <div className="max-w-3xl mx-auto">
        <img
          src="/veritas-logo.png"
          alt="Veritas"
          className="h-8 sm:h-10 mb-6 object-contain"
        />
        <h1 className="text-4xl sm:text-6xl font-semibold leading-tight tracking-tight">
          Is that video<br />
          <span className="text-accent">actually true?</span>
        </h1>
        <p className="mt-6 text-textSecondary text-lg max-w-xl">
          Drop in a link from TikTok, Instagram, Facebook, or X. Veritas pulls out
          the claims, checks them against real sources, and tells you if the footage
          has been floating around the internet long before the post you're looking at.
        </p>
        <p className="mt-3 text-xs text-textMuted max-w-xl">
          Heads up: YouTube often blocks our free demo server, so YouTube links are hit or miss. TikTok works best.
        </p>

        <div className="mt-10">
          <div className="relative">
            <Link2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-textMuted" />
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Paste a video URL..."
              disabled={loading}
              className="w-full bg-surface border border-border focus:border-accent rounded-2xl pl-12 pr-4 py-4 text-base outline-none transition-colors placeholder:text-textMuted disabled:opacity-60"
            />
          </div>

          <button
            onClick={() => onSubmit(url)}
            disabled={loading || !url.trim()}
            className="mt-3 w-full bg-accent hover:bg-accentDark disabled:bg-surfaceLight disabled:text-textMuted text-bg font-semibold py-4 rounded-2xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Working on it...
              </>
            ) : (
              "Check this video"
            )}
          </button>

          {loading && (
            <div className="mt-4">
              <div className="w-full h-1 bg-surface rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent transition-all duration-500"
                  style={{ width: `${Math.max(5, progress)}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-xs text-textSecondary">
                <span>{progressMsg || "Working..."}</span>
                <span className="text-accent">{progress}%</span>
              </div>
              <p className="mt-3 text-xs text-textMuted">
                Usually takes 1 to 3 minutes. First scan after the server wakes up is always the slowest. You can leave this tab open.
              </p>
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-start gap-2 bg-danger/10 border border-danger/25 text-danger text-sm rounded-xl p-3">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!loading && (
            <div className="mt-6 flex flex-wrap gap-2">
              <span className="text-xs text-textMuted mr-1 self-center">Try one of these:</span>
              {EXAMPLES.map((e) => (
                <button
                  key={e.url}
                  onClick={() => setUrl(e.url)}
                  className="text-xs border border-border hover:border-accent hover:text-accent text-textSecondary rounded-full px-3 py-1 transition-colors"
                >
                  {e.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
