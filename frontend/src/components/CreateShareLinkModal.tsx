"use client";

import { useState, useEffect } from "react";
import { createShareLink } from "@/lib/api";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import type { ShareLink, TradeDirection } from "@/lib/types";

interface Props {
  profileId: number;
  hasTradeKey?: boolean;
  onClose: () => void;
  onCreated: (link: ShareLink) => void;
}

const DURATION_OPTIONS = [
  { label: "Unlimited", value: null },
  { label: "1 day", value: 1 },
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
];

export default function CreateShareLinkModal({ profileId, hasTradeKey = false, onClose, onCreated }: Props) {
  const [showTotalValue, setShowTotalValue] = useState(true);
  const [showCoinAmounts, setShowCoinAmounts] = useState(false);
  const [showExchangeNames, setShowExchangeNames] = useState(false);
  const [showAllocationPct, setShowAllocationPct] = useState(true);
  const [allowFollow, setAllowFollow] = useState(true);
  const [durationDays, setDurationDays] = useState<number | null>(null);
  const [label, setLabel] = useState("");
  // Trade delegation (off by default; requires a trade key on the profile)
  const [canTrade, setCanTrade] = useState(false);
  const [tradeDirection, setTradeDirection] = useState<TradeDirection>("both");
  const [allowedCoins, setAllowedCoins] = useState("");
  const [maxPerOrder, setMaxPerOrder] = useState("");
  const [dailyLimit, setDailyLimit] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const trapRef = useFocusTrap(true);

  const numOrNull = (v: string): number | null => {
    const n = parseFloat(v);
    return v.trim() !== "" && !Number.isNaN(n) && n > 0 ? n : null;
  };

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [onClose])

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    try {
      let expiresAt: string | null = null;
      if (durationDays !== null) {
        const d = new Date();
        d.setDate(d.getDate() + durationDays);
        expiresAt = d.toISOString();
      }
      const link = await createShareLink({
        profile_id: profileId,
        show_total_value: showTotalValue,
        show_coin_amounts: showCoinAmounts,
        show_exchange_names: showExchangeNames,
        show_allocation_pct: showAllocationPct,
        expires_at: expiresAt,
        label: label.trim() || null,
        allow_follow: allowFollow,
        can_trade: canTrade,
        trade_direction: tradeDirection,
        trade_allowed_coins: canTrade && allowedCoins.trim() ? allowedCoins.trim().toUpperCase() : null,
        trade_max_per_order_usd: canTrade ? numOrNull(maxPerOrder) : null,
        trade_daily_limit_usd: canTrade ? numOrNull(dailyLimit) : null,
      });
      onCreated(link);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create link");
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
        aria-labelledby="create-share-link-modal-title"
        className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-xl"
      >
        <h2 id="create-share-link-modal-title" className="text-lg font-semibold text-white mb-5">Create Share Link</h2>

        {/* Permissions */}
        <div className="space-y-3 mb-5">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Permissions</p>
          {[
            { label: "Show total value", value: showTotalValue, set: setShowTotalValue },
            { label: "Show coin amounts", value: showCoinAmounts, set: setShowCoinAmounts },
            { label: "Show exchange names", value: showExchangeNames, set: setShowExchangeNames },
            { label: "Show allocation %", value: showAllocationPct, set: setShowAllocationPct },
          { label: "Allow others to follow this portfolio", value: allowFollow, set: setAllowFollow },
          ].map(({ label, value, set }) => (
            <label key={label} className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 accent-blue-500"
                checked={value}
                onChange={(e) => set(e.target.checked)}
              />
              <span className="text-sm text-gray-300">{label}</span>
            </label>
          ))}
        </div>

        {/* Duration */}
        <div className="mb-5">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            Expiry
          </p>
          <div className="flex flex-wrap gap-2">
            {DURATION_OPTIONS.map((opt) => (
              <button
                key={opt.label}
                onClick={() => setDurationDays(opt.value)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  durationDays === opt.value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Label */}
        <div className="mb-6">
          <label htmlFor="share-link-label" className="text-xs font-medium text-gray-400 uppercase tracking-wider block mb-1">
            Label (optional)
          </label>
          <input
            id="share-link-label"
            type="text"
            placeholder="e.g. For accountant"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            maxLength={100}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
          />
        </div>

        {/* Trading delegation */}
        <div className="mb-6 border-t border-gray-800 pt-4">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Trading</p>
          <label className={`flex items-center gap-3 ${hasTradeKey ? "cursor-pointer" : "opacity-60 cursor-not-allowed"}`}>
            <input
              type="checkbox"
              className="w-4 h-4 accent-amber-500"
              checked={canTrade}
              disabled={!hasTradeKey}
              onChange={(e) => setCanTrade(e.target.checked)}
            />
            <span className="text-sm text-gray-300">Allow buy/sell trading</span>
          </label>
          {!hasTradeKey && (
            <p className="mt-1 text-xs text-gray-500">Add a trade key to this profile to enable delegated trading.</p>
          )}

          {canTrade && hasTradeKey && (
            <div className="mt-3 space-y-3 rounded-lg bg-amber-500/5 border border-amber-500/20 p-3">
              <p className="text-xs text-amber-300/90">
                The holder can place spot buy/sell orders within these limits. Withdrawals and transfers are never possible. All limits are optional and can be changed later.
              </p>
              <div>
                <span className="block text-xs text-gray-400 mb-1">Direction</span>
                <div className="flex gap-2">
                  {(["both", "buy", "sell"] as TradeDirection[]).map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setTradeDirection(d)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                        tradeDirection === d ? "bg-amber-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                      }`}
                    >
                      {d === "both" ? "Buy & Sell" : d}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label htmlFor="allowed-coins" className="block text-xs text-gray-400 mb-1">Allowed coins (optional, comma-separated)</label>
                <input
                  id="allowed-coins"
                  type="text"
                  placeholder="e.g. BTC, ETH — empty = all"
                  value={allowedCoins}
                  onChange={(e) => setAllowedCoins(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-amber-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label htmlFor="max-per-order" className="block text-xs text-gray-400 mb-1">Max per order (USD)</label>
                  <input
                    id="max-per-order"
                    type="number"
                    min="0"
                    placeholder="No limit"
                    value={maxPerOrder}
                    onChange={(e) => setMaxPerOrder(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-amber-500"
                  />
                </div>
                <div>
                  <label htmlFor="daily-limit" className="block text-xs text-gray-400 mb-1">24h limit (USD)</label>
                  <input
                    id="daily-limit"
                    type="number"
                    min="0"
                    placeholder="No limit"
                    value={dailyLimit}
                    onChange={(e) => setDailyLimit(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-amber-500"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {error && <p role="alert" className="text-sm text-red-400 mb-4">{error}</p>}

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Creating..." : "Create Link"}
          </button>
        </div>
      </div>
    </div>
  );
}
