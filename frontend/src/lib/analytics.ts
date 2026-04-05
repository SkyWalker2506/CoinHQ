export function trackEvent(name: string, props?: Record<string, string | number>) {
  if (typeof window !== 'undefined' && (window as any).plausible) {
    (window as any).plausible(name, { props })
  }
}

export const events = {
  exchangeConnected: (exchange: string) => trackEvent('Exchange Connected', { exchange }),
  shareLinkCopied: () => trackEvent('Share Link Copied'),
  profileCreated: () => trackEvent('Profile Created'),
  shareLinkViewed: (token: string) => trackEvent('Share Link Viewed'),
}
