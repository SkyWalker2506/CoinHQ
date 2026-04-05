"use client";

import { useState, useEffect } from "react";
import { addKey } from "@/lib/api";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import type { SupportedExchange } from "@/lib/types";
import { events } from "@/lib/analytics";

const EXCHANGES: SupportedExchange[] = ["binance", "bybit", "okx", "coinbase", "kraken"];

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
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose])

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div
        ref={trapRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-key-modal-title"
        className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md"
      >
        <h2 id="add-key-modal-title" className="text-lg font-semibold text-white mb-4">Add Exchange API Key</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="exchange-select" className="block text-sm text-gray-400 mb-1">Exchange</label>
            <select
              id="exchange-select"
              value={exchange}
              onChange={(e) => setExchange(e.target.value as SupportedExchange)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            >
              {EXCHANGES.map((ex) => (
                <option key={ex} value={ex}>
                  {ex.charAt(0).toUpperCase() + ex.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="api-key" className="block text-sm text-gray-400 mb-1">API Key</label>
            <input
              id="api-key"
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste your read-only API key"
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm font-mono focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            />
          </div>
          <div>
            <label htmlFor="api-secret" className="block text-sm text-gray-400 mb-1">
              API Secret
              {exchange === "okx" && (
                <span className="ml-2 text-xs text-yellow-400">
                  OKX: use format secret|passphrase
                </span>
              )}
            </label>
            <input
              id="api-secret"
              type="password"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder="Paste your API secret"
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm font-mono focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            />
          </div>
          <p className="text-xs text-gray-500">
            Keys are encrypted with AES-256 before storage. Only read-only keys are accepted.
          </p>
          {error && <p role="alert" className="text-red-400 text-sm">{error}</p>}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !apiKey.trim() || !apiSecret.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
            >
              {loading ? "Validating & Saving..." : "Save Key"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
