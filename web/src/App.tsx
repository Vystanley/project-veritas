import { useState } from "react";
import { Hero } from "./components/Hero";
import { Results } from "./components/Results";
import { HowItWorks } from "./components/HowItWorks";
import { Footer } from "./components/Footer";
import { ColdStartBanner } from "./components/ColdStartBanner";
import { runFactCheck } from "./api";
import type { FactCheckResult, JobStatus } from "./types";

const SUPPORTED = [
  "tiktok.com", "vt.tiktok.com", "vm.tiktok.com",
  "instagram.com", "youtube.com", "youtu.be",
  "facebook.com", "fb.watch",
  "twitter.com", "x.com",
  "linkedin.com",
];

function validateUrl(url: string): string | null {
  const t = url.trim();
  if (!t) return "Please paste a video link.";
  if (!/^https?:\/\//i.test(t)) return "URL must start with https://";
  if (!SUPPORTED.some((d) => t.toLowerCase().includes(d))) {
    return "Unsupported platform. Try TikTok, Instagram, YouTube, Facebook, X, or LinkedIn.";
  }
  return null;
}

export default function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState("");
  const [result, setResult] = useState<FactCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(videoUrl: string) {
    const validation = validateUrl(videoUrl);
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    setResult(null);
    setLoading(true);
    setProgress(5);
    setProgressMsg("Submitting...");

    try {
      const final = await runFactCheck(videoUrl, (s: JobStatus) => {
        setProgress(s.progress || 0);
        setProgressMsg(s.progress_message || "Working...");
      });
      if (final.status === "completed" && final.result) {
        setResult(final.result);
      } else {
        setError(final.error || "Analysis failed. Please try again.");
      }
    } catch (e: any) {
      setError(e?.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <ColdStartBanner />
      <main className="flex-1">
        <Hero
          url={url}
          setUrl={setUrl}
          onSubmit={handleSubmit}
          loading={loading}
          progress={progress}
          progressMsg={progressMsg}
          error={error}
        />
        {result && <Results result={result} />}
        {!result && !loading && <HowItWorks />}
      </main>
      <Footer />
    </div>
  );
}
