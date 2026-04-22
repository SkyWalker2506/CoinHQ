"use client";

import { useEffect } from "react";
import { events } from "@/lib/analytics";

/**
 * Fires the shareLinkViewed analytics event once when the public share page mounts.
 * Must be a client component because analytics relies on browser APIs (window.plausible).
 */
export default function ShareViewTracker({ token }: { token: string }) {
  useEffect(() => {
    events.shareLinkViewed(token);
  }, [token]);

  return null;
}
