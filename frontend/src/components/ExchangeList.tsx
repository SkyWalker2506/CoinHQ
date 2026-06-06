"use client";

import { useState } from "react";
import type { ExchangeBalance } from "@/lib/types";
import { EmptyState } from "./EmptyState";

interface Props {
  exchanges: ExchangeBalance[];
  onAddKey?: () => void;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

function formatAmount(value: number): string {
  if (value >= 1000) return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (value >= 1) return value.toFixed(4);
  return value.toFixed(6);
}

function ExchangeItem({
  exchange,
  total,
  search,
}: {
  exchange: ExchangeBalance;
  total: number;
  search: string;
}) {
  const [showAll, setShowAll] = useState(false);

  const sorted = [...exchange.balances].sort(
    (a, b) => (b.usd_value ?? 0) - (a.usd_value ?? 0)
  );

  const filtered = search
    ? sorted.filter((b) => b.asset.toLowerCase().includes(search.toLowerCase()))
    : sorted;

  const displayed = search || showAll ? filtered : filtered.slice(0, 5);
  const exchangePct = total > 0 ? ((exchange.total_usd / total) * 100).toFixed(1) : "0";

  return (
    <div className="rounded-lg border border-gray-700 overflow-hidden">
      {/* Exchange header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-800/60">
        <span className="text-sm font-bold text-white capitalize tracking-wide">
          {exchange.exchange}
        </span>
        <div className="text-right">
          <span className="text-sm font-semibold text-white">{formatUsd(exchange.total_usd)}</span>
          <span className="ml-2 text-xs text-gray-400">{exchangePct}%</span>
        </div>
      </div>

      {/* Asset rows */}
      <div className="divide-y divide-gray-800">
        {displayed.length === 0 && (
          <p className="text-sm text-gray-500 px-4 py-3">No results for &ldquo;{search}&rdquo;</p>
        )}
        {displayed.map((balance) => {
          const pct =
            exchange.total_usd > 0 && balance.usd_value
              ? ((balance.usd_value / exchange.total_usd) * 100).toFixed(1)
              : null;

          const noPriceBadge = (balance.usd_value === 0 || balance.usd_value === undefined);

          return (
            <div
              key={balance.asset}
              className="flex items-center justify-between px-4 py-2.5"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-300 shrink-0">
                  {balance.asset.slice(0, 2)}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white flex items-center gap-1.5">
                    {balance.asset}
                    {noPriceBadge && (
                      <span className="text-[10px] text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded font-normal">no price</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500">{formatAmount(balance.total)}</p>
                </div>
              </div>
              <div className="text-right shrink-0 ml-4">
                <p className="text-sm font-medium text-white">
                  {balance.usd_value ? formatUsd(balance.usd_value) : "—"}
                </p>
                {pct && !noPriceBadge && <p className="text-xs text-gray-500">{pct}%</p>}
              </div>
            </div>
          );
        })}
      </div>

      {!search && filtered.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full py-2.5 text-xs text-blue-400 hover:text-blue-300 hover:bg-gray-800/40 transition-colors border-t border-gray-800"
        >
          {showAll ? "Show less" : `Show all ${filtered.length} assets`}
        </button>
      )}
    </div>
  );
}

const EXCHANGE_LABELS: Record<string, string> = {
  binance: "BNC",
  binancetr: "BNCTR",
  bybit: "BBT",
  okx: "OKX",
  coinbase: "CB",
  kraken: "KRK",
};

export default function ExchangeList({ exchanges, onAddKey }: Props) {
  const [search, setSearch] = useState("");
  const [activeExchange, setActiveExchange] = useState<string | null>(null);

  if (exchanges.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <EmptyState
          icon="🔗"
          title="No exchanges connected"
          description="Add your read-only API keys to start tracking your portfolio."
          action={onAddKey ? { label: "Connect exchange", onClick: onAddKey } : undefined}
        />
      </div>
    );
  }

  const total = exchanges.reduce((acc, e) => acc + e.total_usd, 0);
  const filtered = activeExchange
    ? exchanges.filter((e) => e.exchange === activeExchange)
    : exchanges;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Exchange Balances
        </h3>
      </div>

      {/* Exchange filter tabs */}
      {exchanges.length > 1 && (
        <div className="flex gap-1.5 mb-3 flex-wrap">
          <button
            onClick={() => setActiveExchange(null)}
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
              activeExchange === null ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            ALL
          </button>
          {exchanges.map((e) => (
            <button
              key={e.exchange}
              onClick={() => setActiveExchange(activeExchange === e.exchange ? null : e.exchange)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                activeExchange === e.exchange ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {EXCHANGE_LABELS[e.exchange] ?? e.exchange.toUpperCase()}
            </button>
          ))}
        </div>
      )}

      {/* Search */}
      <div className="relative mb-4">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 105 11a6 6 0 0012 0z" />
        </svg>
        <input
          type="text"
          placeholder="Search coin (BTC, ETH…)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
          >
            ✕
          </button>
        )}
      </div>

      <div className="space-y-3">
        {filtered.map((exchange, idx) => (
          <ExchangeItem key={idx} exchange={exchange} total={total} search={search} />
        ))}
      </div>
    </div>
  );
}
