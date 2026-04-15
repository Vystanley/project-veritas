import { Github } from "lucide-react";

const REPO = "https://github.com/Vystanley/project-veritas";

export function Footer() {
  return (
    <footer className="border-t border-border mt-auto">
      <div className="max-w-5xl mx-auto px-4 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="text-sm text-textSecondary">
          © {new Date().getFullYear()} Veritas. A student portfolio project.
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          <a
            href={`${REPO}/blob/main/DISCLAIMER.md`}
            target="_blank"
            rel="noreferrer noopener"
            className="text-textSecondary hover:text-accent transition-colors"
          >
            Disclaimer
          </a>
          <a
            href={`${REPO}/blob/main/TERMS_OF_USE.md`}
            target="_blank"
            rel="noreferrer noopener"
            className="text-textSecondary hover:text-accent transition-colors"
          >
            Terms
          </a>
          <a
            href={`${REPO}/blob/main/PRIVACY_POLICY.md`}
            target="_blank"
            rel="noreferrer noopener"
            className="text-textSecondary hover:text-accent transition-colors"
          >
            Privacy
          </a>
          <a
            href={REPO}
            target="_blank"
            rel="noreferrer noopener"
            className="text-textSecondary hover:text-accent transition-colors flex items-center gap-1"
          >
            <Github className="w-4 h-4" />
            Source
          </a>
        </div>
      </div>
    </footer>
  );
}
