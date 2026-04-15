import { Info } from "lucide-react";

export function ColdStartBanner() {
  return (
    <div className="w-full border-b border-border bg-surface/60 backdrop-blur">
      <div className="max-w-5xl mx-auto px-4 py-2 flex items-center gap-2 text-xs text-textSecondary">
        <Info className="w-3.5 h-3.5 text-accent flex-shrink-0" />
        <span>
          Heads up: the demo runs on a free server, so the first scan can take{" "}
          <span className="text-textPrimary">2 to 3 minutes</span> while it wakes up. Videos up to 5 minutes, 3 scans a day.
        </span>
      </div>
    </div>
  );
}
