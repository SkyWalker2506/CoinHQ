declare global {
  interface Window {
    plausible?: (name: string, options?: { props?: Record<string, string | number> }) => void;
  }
}

export function trackEvent(name: string, props?: Record<string, string | number>) {
  if (typeof window !== 'undefined' && window.plausible) {
    window.plausible(name, { props })
  }
}

export const events = {
  exchangeConnected: (exchange: string) => trackEvent('Exchange Connected', { exchange }),
  shareLinkCopied: () => trackEvent('Share Link Copied'),
  profileCreated: () => trackEvent('Profile Created'),
  shareLinkViewed: (_token: string) => trackEvent('Share Link Viewed'),
}
