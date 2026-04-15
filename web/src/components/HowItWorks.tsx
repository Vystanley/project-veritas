import { Link2, Brain, FileCheck } from "lucide-react";

const STEPS = [
  {
    icon: Link2,
    title: "Paste a video link",
    body: "Works with TikTok, YouTube, Instagram, Facebook, and X. Just the URL, nothing else.",
  },
  {
    icon: Brain,
    title: "We break it down",
    body: "Veritas listens to the audio, looks at the visuals, pulls out the factual claims, and runs a reverse image search on a key frame to see if the footage is actually new.",
  },
  {
    icon: FileCheck,
    title: "You get a verdict",
    body: "Every claim comes back with a source you can click through and read for yourself. No black box.",
  },
];

export function HowItWorks() {
  return (
    <section className="px-4 py-20 border-t border-border">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-semibold">How it works</h2>
        <p className="mt-2 text-textSecondary">Three steps, no sign-up for the demo.</p>

        <div className="mt-10 grid gap-4 sm:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={i} className="border border-border rounded-2xl p-6 bg-surface/40">
              <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/25 flex items-center justify-center">
                <s.icon className="w-5 h-5 text-accent" />
              </div>
              <div className="mt-4 text-xs text-textMuted">Step {i + 1}</div>
              <h3 className="mt-1 font-semibold text-textPrimary">{s.title}</h3>
              <p className="mt-2 text-sm text-textSecondary leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 border border-border rounded-2xl p-6 bg-surface/40">
          <h3 className="font-semibold">One thing before you use it</h3>
          <p className="mt-2 text-sm text-textSecondary leading-relaxed">
            This is a research preview, not a finished product. Verdicts can be wrong, especially on breaking news or
            anything really technical. Click the sources and read them yourself before you trust anything it says. And
            please don't use it for legal, medical, financial, or safety decisions. Those need a real expert.
          </p>
        </div>
      </div>
    </section>
  );
}
