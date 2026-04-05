"use client";

import { useState, useEffect } from "react";
import { addKey } from "@/lib/api";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import type { SupportedExchange } from "@/lib/types";
import { events } from "@/lib/analytics";

const EXCHANGES: SupportedExchange[] = ["binance", "bybit", "okx", "coinbase", "kraken"];

interface ExchangeInfo {
  webUrl: string;
  appScheme: string | null; // deep link scheme
  iosUrl: string | null;    // App Store
  androidUrl: string | null; // Play Store
}

const EXCHANGE_INFO: Record<SupportedExchange, ExchangeInfo> = {
  binance: {
    webUrl: "https://www.binance.com/en/my/settings/api-management",
    appScheme: "binance://",
    iosUrl: "https://apps.apple.com/app/binance-buy-bitcoin-crypto/id1436799971",
    androidUrl: "https://play.google.com/store/apps/details?id=com.binance.dev",
  },
  bybit: {
    webUrl: "https://www.bybit.com/app/user/api-management",
    appScheme: "bybit://",
    iosUrl: "https://apps.apple.com/app/bybit-buy-crypto-bitcoin/id1488296980",
    androidUrl: "https://play.google.com/store/apps/details?id=com.bybit.app",
  },
  okx: {
    webUrl: "https://www.okx.com/account/my-api",
    appScheme: "okx://",
    iosUrl: "https://apps.apple.com/app/okx-buy-bitcoin-btc-crypto/id1327268470",
    androidUrl: "https://play.google.com/store/apps/details?id=com.okinc.okex.gp",
  },
  coinbase: {
    webUrl: "https://www.coinbase.com/settings/api",
    appScheme: "coinbase://",
    iosUrl: "https://apps.apple.com/app/coinbase-buy-bitcoin-ether/id886427730",
    androidUrl: "https://play.google.com/store/apps/details?id=com.coinbase.android",
  },
  kraken: {
    webUrl: "https://www.kraken.com/u/security/api",
    appScheme: null,
    iosUrl: "https://apps.apple.com/app/kraken-buy-bitcoin-crypto/id1481947260",
    androidUrl: "https://play.google.com/store/apps/details?id=com.kraken.trade",
  },
};

function openExchangeLink(info: ExchangeInfo) {
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  if (isMobile && info.appScheme) {
    // Try app deep link, fall back to web after 1.5s
    const fallbackTimer = setTimeout(() => {
      window.open(info.webUrl, "_blank", "noopener,noreferrer");
    }, 1500);

    const iframe = document.createElement("iframe");
    iframe.style.display = "none";
    iframe.src = info.appScheme;
    document.body.appendChild(iframe);

    window.addEventListener("blur", () => clearTimeout(fallbackTimer), { once: true });
    setTimeout(() => document.body.removeChild(iframe), 3000);
  } else {
    window.open(info.webUrl, "_blank", "noopener,noreferrer");
  }
}

interface Props {
  profileId: number;
  onClose: () => void;
  onAdded: () => void;
}

export default function AddKeyModal({ profileId, onClose, onAdded }: Props) {
  const [exchange, setExchange] = useState<SupportedExchange>("binance");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const trapRef = useFocusTrap(true);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim() || !apiSecret.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await addKey(profileId, exchange, apiKey.trim(), apiSecret.trim());
      events.exchangeConnected(exchange);
      onAdded();
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const info = EXCHANGE_INFO[exchange];
  const isMobile = typeof navigator !== "undefined" && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 px-0 sm:px-4">
      <div
        ref={trapRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-key-modal-title"
        className="bg-gray-900 border border-gray-700 rounded-t-2xl sm:rounded-xl p-5 sm:p-6 w-full sm:max-w-md max-h-[92vh] overflow-y-auto"
      >
        <h2 id="add-key-modal-title" className="text-lg font-semibold text-white mb-4">
          Add Exchange API Key
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Exchange selector */}
          <div>
            <label htmlFor="exchange-select" className="block text-sm text-gray-400 mb-1">
              Exchange
            </label>
            <select
              id="exchange-select"
              value={exchange}
              onChange={(e) => setExchange(e.target.value as SupportedExchange)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2.5 text-white text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            >
              {EXCHANGES.map((ex) => (
                <option key={ex} value={ex}>
                  {ex.charAt(0).toUpperCase() + ex.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Smart exchange link */}
          <div className="bg-gray-800 rounded-lg p-3 flex items-start gap-3">
            <svg className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-400 mb-2">
                {isMobile
                  ? "API key yönetimi genellikle web üzerinden yapılır. Aşağıdan borsaya gidin:"
                  : "API key oluşturmak için borsanın sitesine gidin:"}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => openExchangeLink(info)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg font-medium transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  {exchange.charAt(0).toUpperCase() + exchange.slice(1)} API Yönetimi
                </button>
                {isMobile && (
                  <>
                    {info.iosUrl && /iPhone|iPad|iPod/i.test(navigator.userAgent) && (
                      <a
                        href={info.iosUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded-lg transition-colors"
                      >
                        App Store
                      </a>
                    )}
                    {info.androidUrl && /Android/i.test(navigator.userAgent) && (
                      <a
                        href={info.androidUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded-lg transition-colors"
                      >
                        Play Store
                      </a>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* API Key */}
          <div>
            <label htmlFor="api-key" className="block text-sm text-gray-400 mb-1">API Key</label>
            <input
              id="api-key"
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste your read-only API key"
              autoComplete="off"
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2.5 text-white text-sm font-mono focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            />
          </div>

          {/* API Secret */}
          <div>
            <label htmlFor="api-secret" className="block text-sm text-gray-400 mb-1">
              API Secret
              {exchange === "okx" && (
                <span className="ml-2 text-xs text-yellow-400">OKX: secret|passphrase</span>
              )}
            </label>
            <input
              id="api-secret"
              type="password"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder="Paste your API secret"
              autoComplete="off"
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2.5 text-white text-sm font-mono focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            />
          </div>

          <p className="text-xs text-gray-500">
            Keys are encrypted with AES-256 before storage. Only read-only keys are accepted.
          </p>
          {error && <p role="alert" className="text-red-400 text-sm">{error}</p>}

          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !apiKey.trim() || !apiSecret.trim()}
              className="flex-1 sm:flex-none px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
            >
              {loading ? "Validating…" : "Save Key"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
