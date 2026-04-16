import { useState } from "react";
import {
  CheckCircle2, XCircle, AlertTriangle, HelpCircle,
  FileText, Eye, Shield, Images, ChevronDown, ChevronUp, ExternalLink,
  RotateCcw, Link2, Copy, Check,
} from "lucide-react";
import type { FactCheckResult } from "../types";

function verdictStyle(verdict: string) {
  const v = verdict.toLowerCase();
  if (v === "true") return { color: "#4CAF50", icon: CheckCircle2, label: "True" };
  if (v.includes("mostly true")) return { color: "#8BC34A", icon: CheckCircle2, label: "Mostly true" };
  if (v.includes("partially")) return { color: "#F59E0B", icon: AlertTriangle, label: "Partially true" };
  if (v.includes("mostly false")) return { color: "#E67E22", icon: XCircle, label: "Mostly false" };
  if (v === "false") return { color: "#E74C3C", icon: XCircle, label: "False" };
  return { color: "#999999", icon: HelpCircle, label: verdict || "Inconclusive" };
}

interface Props {
  result: FactCheckResult;
  scannedUrl?: string;
  onScanAnother?: () => void;
}

export function Results({ result, scannedUrl, onScanAnother }: Props) {
  const v = verdictStyle(result.overall_verdict);
  const Icon = v.icon;
  const [copied, setCopied] = useState(false);

  function copyVerdict() {
    const lines = [
      `Verdict: ${result.overall_verdict} (${Math.round(result.confidence_score)}% confidence)`,
      result.summary,
      "",
      `Claims (${result.claims?.length || 0}):`,
      ...(result.claims || []).map(
        (c, i) => `${i + 1}. [${c.verdict}] ${c.claim}`
      ),
      "",
      scannedUrl ? `Video: ${scannedUrl}` : "",
      "Checked by Veritas — https://project-veritas-mauve.vercel.app",
    ];
    navigator.clipboard.writeText(lines.filter(Boolean).join("\n")).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <section className="px-4 pb-16">
      <div className="max-w-3xl mx-auto space-y-4">
        {/* Scanned-URL chip — lets the user see what they just checked without
            scrolling back to the input. */}
        {scannedUrl && (
          <a
            href={scannedUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="flex items-center gap-2 text-xs text-textMuted hover:text-accent transition-colors px-1 -mb-2"
          >
            <Link2 className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="truncate">{scannedUrl}</span>
          </a>
        )}

        {/* Verdict card */}
        <div
          className="rounded-2xl border p-6 sm:p-8"
          style={{ borderColor: `${v.color}40`, backgroundColor: `${v.color}10` }}
        >
          <div className="flex items-start gap-4">
            <Icon className="w-10 h-10 flex-shrink-0" style={{ color: v.color }} />
            <div className="flex-1 min-w-0">
              <div className="text-xs uppercase tracking-widest text-textSecondary">Overall verdict</div>
              <div className="mt-1 text-3xl font-semibold" style={{ color: v.color }}>
                {v.label}
              </div>
              <div className="mt-1 text-sm text-textSecondary">
                {Math.round(result.confidence_score)}% confidence
              </div>
              {result.summary && (
                <p className="mt-4 text-[15px] leading-relaxed text-textPrimary/90">{result.summary}</p>
              )}
              <button
                onClick={copyVerdict}
                className="mt-4 flex items-center gap-1.5 text-xs text-textSecondary hover:text-accent transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Copied!" : "Copy verdict"}
              </button>
            </div>
          </div>
        </div>

        {/* Claims */}
        {result.claims?.length > 0 && (
          <Collapsible title="Claims analyzed" icon={FileText} defaultOpen count={result.claims.length}>
            <div className="space-y-3">
              {result.claims.map((c, i) => {
                const cv = verdictStyle(c.verdict);
                return (
                  <div key={i} className="border border-border rounded-xl p-4 bg-surface">
                    <div className="flex items-start gap-2">
                      <span
                        className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded"
                        style={{ backgroundColor: `${cv.color}20`, color: cv.color }}
                      >
                        {cv.label}
                      </span>
                    </div>
                    <p className="mt-2 text-[15px] text-textPrimary">"{c.claim}"</p>
                    <p className="mt-2 text-sm text-textSecondary leading-relaxed">{c.explanation}</p>
                  </div>
                );
              })}
            </div>
          </Collapsible>
        )}

        {/* Sources */}
        {result.sources?.length > 0 && (
          <Collapsible title="Sources" icon={ExternalLink} count={result.sources.length}>
            <div className="space-y-2">
              {result.sources.map((s, i) => (
                <a
                  key={i}
                  href={s.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="block border border-border hover:border-accent rounded-xl p-3 bg-surface transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-medium text-textPrimary text-sm group-hover:text-accent">{s.title}</div>
                    <ExternalLink className="w-4 h-4 text-textMuted flex-shrink-0 mt-0.5" />
                  </div>
                  <div className="text-xs text-textMuted mt-1 truncate">{s.url}</div>
                  {s.description && (
                    <div className="text-xs text-textSecondary mt-2 line-clamp-2">{s.description}</div>
                  )}
                </a>
              ))}
            </div>
          </Collapsible>
        )}

        {/* Reverse image search */}
        {result.reverse_image?.enabled && (
          <Collapsible title="Reverse image search" icon={Images}>
            {result.reverse_image.earliest_date && (
              <div className="text-sm text-warn mb-3">
                Earliest match found: <span className="font-semibold">{result.reverse_image.earliest_date}</span>
                {result.reverse_image.note && (
                  <div className="mt-1 text-xs text-textSecondary">{result.reverse_image.note}</div>
                )}
              </div>
            )}
            {result.reverse_image.matches?.length > 0 ? (
              <div className="space-y-2">
                {result.reverse_image.matches.slice(0, 8).map((m, i) => (
                  <a
                    key={i}
                    href={m.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="block border border-border hover:border-accent rounded-xl p-3 bg-surface transition-colors"
                  >
                    <div className="text-sm text-textPrimary">{m.title || m.source}</div>
                    <div className="text-xs text-textMuted mt-1 flex gap-2">
                      <span>{m.source}</span>
                      {m.date && <span>· {m.date}</span>}
                    </div>
                  </a>
                ))}
              </div>
            ) : (
              <div className="text-sm text-textSecondary">No similar frames found online.</div>
            )}
          </Collapsible>
        )}

        {/* Deepfake */}
        {result.deepfake && (
          <Collapsible title="Deepfake check" icon={Shield}>
            <div className="text-sm space-y-2">
              <div>
                <span className="text-textSecondary">Risk level: </span>
                <span className="font-semibold">{result.deepfake.risk_level}</span>
                <span className="text-textMuted"> ({Math.round(result.deepfake.confidence || 0)}%)</span>
              </div>
              <p className="text-textSecondary leading-relaxed">{result.deepfake.analysis}</p>
              {result.deepfake.indicators?.length > 0 && (
                <ul className="list-disc list-inside text-textSecondary space-y-1">
                  {result.deepfake.indicators.map((ind, i) => (
                    <li key={i}>{ind}</li>
                  ))}
                </ul>
              )}
            </div>
          </Collapsible>
        )}

        {/* Transcript */}
        {result.transcript && (
          <Collapsible title="Transcript" icon={FileText}>
            <p className="text-sm text-textSecondary whitespace-pre-wrap leading-relaxed">{result.transcript}</p>
          </Collapsible>
        )}

        {/* Visual description */}
        {result.visual_description && (
          <Collapsible title="Visual description" icon={Eye}>
            <p className="text-sm text-textSecondary whitespace-pre-wrap leading-relaxed">
              {result.visual_description}
            </p>
          </Collapsible>
        )}

        {onScanAnother && (
          <div className="pt-4 flex justify-center">
            <button
              onClick={onScanAnother}
              className="flex items-center gap-2 border border-border hover:border-accent text-textSecondary hover:text-accent rounded-full px-5 py-2.5 text-sm font-medium transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Check another video
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function Collapsible({
  title,
  icon: Icon,
  children,
  defaultOpen = false,
  count,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  defaultOpen?: boolean;
  count?: number;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-2xl bg-surface/40 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-4 h-4 text-accent" />
          <span className="font-medium">{title}</span>
          {count !== undefined && (
            <span className="text-xs text-textMuted">({count})</span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-textMuted" /> : <ChevronDown className="w-4 h-4 text-textMuted" />}
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}
