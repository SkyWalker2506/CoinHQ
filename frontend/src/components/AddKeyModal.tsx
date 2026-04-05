"use client";

import { useState } from "react";
import { addKey } from "@/lib/api";
import type { SupportedExchange } from "@/lib/types";

const EXCHANGES: SupportedExchange[] = ["binance", "bybit", "okx"];

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim() || !apiSecret.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await addKey(profileId, exchange, apiKey.trim(), apiSecret.trim());
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
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold text-white mb-4">Add Exchange API Key</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Exchange</label>
            <select
              value={exchange}
              onChange={(e) => setExchange(e.target.value as SupportedExchange)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              {EXCHANGES.map((ex) => (
                <option key={ex} value={ex}>
                  {ex.charAt(0).toUpperCase() + ex.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">API Key</label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste your read-only API key"
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              API Secret
              {exchange === "okx" && (
                <span className="ml-2 text-xs text-yellow-400">
                  OKX: use format secret|passphrase
                </span>
              )}
            </label>
            <input
              type="password"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder="Paste your API secret"
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-blue-500"
            />
          </div>
          <p className="text-xs text-gray-500">
            Keys are encrypted with AES-256 before storage. Only read-only keys are accepted.
          </p>
          {error && <p className="text-red-400 text-sm">{error}</p>}
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
