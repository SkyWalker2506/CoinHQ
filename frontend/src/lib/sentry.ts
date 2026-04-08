/**
 * Optional Sentry error tracking — only active when NEXT_PUBLIC_SENTRY_DSN is set.
 * Uses dynamic import to avoid bundle bloat when Sentry is not configured.
 */

let _initialized = false;

async function initSentry() {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn || _initialized || typeof window === 'undefined') return;
  try {
    const Sentry = await import('@sentry/nextjs');
    Sentry.init({
      dsn,
      tracesSampleRate: 0.1,
      environment: process.env.NODE_ENV,
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
