/**
 * Optional Sentry error tracking — only active when NEXT_PUBLIC_SENTRY_DSN is set.
 * Uses dynamic import to avoid bundle bloat when Sentry is not configured.
 */

let _initialized = false;

/**
 * Scrub PII from Sentry events before sending.
 * - Strips query strings (removes ?token=... JWT leaks from /auth/callback)
 * - Redacts share link tokens in URL paths (/share/<token> → /share/[token])
 */
function _scrubEvent(event: Record<string, unknown>): Record<string, unknown> {
  const req = event.request as Record<string, unknown> | undefined;
  if (req?.url && typeof req.url === 'string') {
    try {
      const url = new URL(req.url);
      // Strip all query parameters (may contain JWTs, tokens)
      url.search = '';
      // Redact share link tokens: /share/<alphanumeric> → /share/[token]
      url.pathname = url.pathname.replace(/\/share\/[A-Za-z0-9_-]{20,}/, '/share/[token]');
      req.url = url.toString();
    } catch {
      // If URL parsing fails, remove it entirely rather than send raw
      delete req.url;
    }
    event.request = req;
  }
  return event;
}

async function initSentry() {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn || _initialized || typeof window === 'undefined') return;
  try {
    const Sentry = await import('@sentry/nextjs');
    Sentry.init({
      dsn,
      tracesSampleRate: 0.1,
      environment: process.env.NODE_ENV,
      beforeSend(event) {
        return _scrubEvent(event as unknown as Record<string, unknown>) as typeof event;
      },
    });
    _initialized = true;
  } catch {
    // Sentry package not installed — silently skip
  }
}

export async function captureError(error: Error, context?: Record<string, unknown>) {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn || typeof window === 'undefined') return;
  try {
    await initSentry();
    const Sentry = await import('@sentry/nextjs');
    Sentry.withScope((scope) => {
      if (context) {
        Object.entries(context).forEach(([key, value]) => {
          scope.setExtra(key, value);
        });
      }
      Sentry.captureException(error);
    });
  } catch {
    // Sentry unavailable — silently skip
  }
}

export { initSentry };
