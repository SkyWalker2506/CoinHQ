"use client";

import { useState } from "react";
import type { TradeDirection, TradeOrder, TradeOrderRequest } from "@/lib/types";

interface Props {
  exchanges: string[];
  direction?: TradeDirection;
  allowedCoins?: string | null;
  maxPerOrderUsd?: number | null;
  dailyLimitUsd?: number | null;
  spentTodayUsd?: number;
  onSubmit: (payload: TradeOrderRequest) => Promise<TradeOrder>;
}

const fmtUsd = (n: number) => `$${n.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;

export default function TradePanel({
  exchanges,
  direction = "both",
  allowedCoins,
  maxPerOrderUsd,
  dailyLimitUsd,
  spentTodayUsd,
  onSubmit,
}: Props) {
  const sides: ("buy" | "sell")[] = direction === "both" ? ["buy", "sell"] : [direction];
  const [exchange, setExchange] = useState(exchanges[0] ?? "");
  const [asset, setAsset] = useState("");
  const [side, setSide] = useState<"buy" | "sell">(sides[0]);
  const [usd, setUsd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TradeOrder | null>(null);

  if (exchanges.length === 0) {
    return <p className="text-sm text-gray-500">No trade key configured for this profile.</p>;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(usd);
    if (!asset.trim() || !(amount > 0)) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const order = await onSubmit({
        exchange,
        asset: asset.trim().toUpperCase(),
        side,
        usd_amount: amount,
      });
      setResult(order);
      setUsd("");
      setAsset("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Order failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      {(allowedCoins || maxPerOrderUsd != null || dailyLimitUsd != null) && (
        <ul className="text-xs text-amber-300/80 space-y-0.5">
          {allowedCoins && <li>Allowed coins: {allowedCoins}</li>}
          {maxPerOrderUsd != null && <li>Max per order: {fmtUsd(maxPerOrderUsd)}</li>}
          {dailyLimitUsd != null && (
            <li>
              24h limit: {fmtUsd(dailyLimitUsd)}
              {spentTodayUsd != null && ` (used ${fmtUsd(spentTodayUsd)})`}
            </li>
          )}
        </ul>
      )}

      <div className="grid grid-cols-2 gap-2">
        {exchanges.length > 1 ? (
          <select
            aria-label="Exchange"
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white capitalize"
          >
            {exchanges.map((ex) => (
              <option key={ex} value={ex}>{ex}</option>
            ))}
          </select>
        ) : (
          <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 capitalize">
            {exchange}
          </div>
        )}
        <input
          aria-label="Asset"
          type="text"
          placeholder="Asset e.g. BTC"
          value={asset}
          onChange={(e) => setAsset(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white uppercase placeholder:normal-case"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        {sides.length > 1 ? (
          <div className="flex gap-2">
            {sides.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSide(s)}
                className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                  side === s
                    ? s === "buy"
                      ? "bg-green-600 text-white"
                      : "bg-red-600 text-white"
                    : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        ) : (
          <div className={`px-3 py-2 rounded-lg text-sm font-medium capitalize text-center ${sides[0] === "buy" ? "bg-green-700/40 text-green-300" : "bg-red-700/40 text-red-300"}`}>
            {sides[0]} only
          </div>
        )}
        <input
          aria-label="USD amount"
          type="number"
          min="0"
          step="any"
          placeholder="USD amount"
          value={usd}
          onChange={(e) => setUsd(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
        />
      </div>

      <button
        type="submit"
        disabled={loading || !asset.trim() || !(parseFloat(usd) > 0)}
        className="w-full px-4 py-2.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
      >
        {loading ? "Placing order…" : `Place ${side} order`}
      </button>

      {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
      {result && (
        <p role="status" className="text-sm text-green-400">
          {result.status === "filled" ? "Order filled" : `Order ${result.status}`}: {result.side} {result.base_asset} for {fmtUsd(result.usd_value)}
        </p>
      )}
    </form>
  );
}
