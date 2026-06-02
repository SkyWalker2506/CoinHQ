"use client";

import { useEffect, useState } from "react";
import { updateShareLink } from "@/lib/api";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import type { ShareLink, TradeDirection } from "@/lib/types";

interface Props {
  link: ShareLink;
  hasTradeKey: boolean;
  onClose: () => void;
  onSaved: (link: ShareLink) => void;
}

export default function EditTradeModal({ link, hasTradeKey, onClose, onSaved }: Props) {
  const [canTrade, setCanTrade] = useState(link.can_trade);
  const [direction, setDirection] = useState<TradeDirection>(link.trade_direction);
  const [allowedCoins, setAllowedCoins] = useState(link.trade_allowed_coins ?? "");
  const [maxPerOrder, setMaxPerOrder] = useState(
    link.trade_max_per_order_usd != null ? String(link.trade_max_per_order_usd) : ""
  );
  const [dailyLimit, setDailyLimit] = useState(
    link.trade_daily_limit_usd != null ? String(link.trade_daily_limit_usd) : ""
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const trapRef = useFocusTrap(true);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  const numOrNull = (v: string): number | null => {
    const n = parseFloat(v);
    return v.trim() !== "" && !Number.isNaN(n) && n > 0 ? n : null;
  };

  const save = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await updateShareLink(link.id, {
        can_trade: canTrade,
        trade_direction: direction,
        trade_allowed_coins: canTrade && allowedCoins.trim() ? allowedCoins.trim().toUpperCase() : null,
        trade_max_per_order_usd: canTrade ? numOrNull(maxPerOrder) : null,
        trade_daily_limit_usd: canTrade ? numOrNull(dailyLimit) : null,
      });
      onSaved(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div
        ref={trapRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-trade-modal-title"
        className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-xl"
      >
        <h2 id="edit-trade-modal-title" className="text-lg font-semibold text-white mb-1">
          Trade permissions
        </h2>
        <p className="text-xs text-gray-400 mb-4">
          Changes apply to the link holder immediately. Withdrawals/transfers are never possible.
        </p>

        <label className={`flex items-center gap-3 mb-3 ${hasTradeKey ? "cursor-pointer" : "opacity-60 cursor-not-allowed"}`}>
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
          <p className="text-xs text-gray-500 mb-3">Add a trade key to this profile to enable trading.</p>
        )}

        {canTrade && hasTradeKey && (
          <div className="space-y-3 rounded-lg bg-amber-500/5 border border-amber-500/20 p-3 mb-4">
            <div>
              <span className="block text-xs text-gray-400 mb-1">Direction</span>
              <div className="flex gap-2">
                {(["both", "buy", "sell"] as TradeDirection[]).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDirection(d)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                      direction === d ? "bg-amber-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                    }`}
                  >
                    {d === "both" ? "Buy & Sell" : d}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="edit-allowed-coins" className="block text-xs text-gray-400 mb-1">Allowed coins (optional)</label>
              <input
                id="edit-allowed-coins"
                type="text"
                placeholder="e.g. BTC, ETH — empty = all"
                value={allowedCoins}
                onChange={(e) => setAllowedCoins(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="edit-max-per-order" className="block text-xs text-gray-400 mb-1">Max per order (USD)</label>
                <input
                  id="edit-max-per-order"
                  type="number"
                  min="0"
                  placeholder="No limit"
                  value={maxPerOrder}
                  onChange={(e) => setMaxPerOrder(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500"
                />
              </div>
              <div>
                <label htmlFor="edit-daily-limit" className="block text-xs text-gray-400 mb-1">24h limit (USD)</label>
                <input
                  id="edit-daily-limit"
                  type="number"
                  min="0"
                  placeholder="No limit"
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500"
                />
              </div>
            </div>
          </div>
        )}

        {error && <p role="alert" className="text-sm text-red-400 mb-3">{error}</p>}

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
            Cancel
          </button>
          <button
            onClick={save}
            disabled={loading}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
