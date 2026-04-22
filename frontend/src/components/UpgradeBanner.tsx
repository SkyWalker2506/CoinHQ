"use client";

import Link from "next/link";
import { useEffect } from "react";
import { trackEvent } from "@/lib/analytics";

interface Props {
  message?: string;
  /** Attribution source shown in analytics. Defaults to 'settings'. */
  source?: string;
}

/**
 * Shown when the backend returns a 403 tier-limit error.
 * Prompts the user to upgrade to Premium.
 * Fires Plausible events on impression and upgrade-click.
 */
export function UpgradeBanner({ message, source = "settings" }: Props) {
  useEffect(() => {
    trackEvent("Upgrade Banner Shown", { source });
  }, [source]);

  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-4 rounded-xl border border-amber-700/60 bg-amber-900/20 px-5 py-4"
    >
      <div className="flex items-center gap-3">
        <span className="text-amber-400 text-lg" aria-hidden="true">⚡</span>
        <div>
          <p className="text-sm font-medium text-amber-300">
            {message ?? "You've reached your free tier limit."}
          </p>
          <p className="text-xs text-amber-500 mt-0.5">
            Upgrade to Premium for unlimited profiles and exchanges.
          </p>
        </div>
      </div>
      <Link
        href="/pricing"
        onClick={() => trackEvent("Upgrade Clicked", { source })}
        className="shrink-0 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-gray-900 text-sm font-semibold rounded-lg transition-colors"
      >
        Upgrade
      </Link>
    </div>
  );
}
