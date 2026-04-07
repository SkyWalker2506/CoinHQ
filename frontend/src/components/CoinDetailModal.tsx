"use client";

import { useEffect, useState } from "react";
import { getCoinInfo } from "@/lib/api";
import type { CoinInfo, MarketCoin } from "@/lib/types";
import { useFocusTrap } from "@/hooks/useFocusTrap";

interface Props {
  symbol: string;
  marketData?: MarketCoin | null;
  onClose: () => void;
}

function fmtUsd(val: number | null | undefined): string {
  if (val == null) return "—";
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtPrice(val: number | null | undefined): string {
  if (val == null) return "—";
  if (val >= 1) return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 8 })}`;
}

function ChangeBadge({ value, label }: { value: number | null | undefined; label: string }) {
  if (value == null) return null;
  const color = value >= 0 ? "text-green-400 bg-green-900/30" : "text-red-400 bg-red-900/30";
  return (
    <div className="text-center">
      <p className="text-[10px] text-gray-500 mb-0.5">{label}</p>
      <span className={`text-xs font-medium px-2 py-0.5 rounded ${color}`}>
        {value >= 0 ? "+" : ""}{value.toFixed(2)}%
      </span>
    </div>
  );
}

export default function CoinDetailModal({ symbol, marketData, onClose }: Props) {
  const [info, setInfo] = useState<CoinInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const trapRef = useFocusTrap(true);

  useEffect(() => {
    getCoinInfo(symbol)
      .then(setInfo)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [symbol]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 px-0 sm:px-4">
      <div
        ref={trapRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="coin-detail-title"
        className="bg-gray-900 border border-gray-700 rounded-t-2xl sm:rounded-xl w-full sm:max-w-lg max-h-[85vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <div className="flex items-center gap-3">
            {info?.logo && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={info.logo} alt={`${symbol} logo`} className="w-8 h-8 rounded-full" />
            )}
            <div>
              <h2 id="coin-detail-title" className="text-lg font-bold text-white">
                {info?.name ?? symbol} <span className="text-gray-500 font-normal text-sm">{symbol}</span>
              </h2>
              {marketData?.rank && (
                <span className="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
                  #{marketData.rank}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-gray-400 hover:text-white p-1"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading coin data...</div>
        ) : (
          <div className="p-5 space-y-5">
            {/* Price & Changes */}
            {marketData && (
              <div>
                <p className="text-2xl font-bold text-white mb-3">{fmtPrice(marketData.price)}</p>
                <div className="flex items-center gap-4">
                  <ChangeBadge value={marketData.change_1h} label="1h" />
                  <ChangeBadge value={marketData.change_24h} label="24h" />
                  <ChangeBadge value={marketData.change_7d} label="7d" />
                </div>
              </div>
            )}

            {/* Market Stats */}
            {marketData && (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-[10px] text-gray-500 uppercase">Market Cap</p>
                  <p className="text-sm font-medium text-white">{fmtUsd(marketData.market_cap)}</p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-[10px] text-gray-500 uppercase">24h Volume</p>
                  <p className="text-sm font-medium text-white">{fmtUsd(marketData.volume_24h)}</p>
                </div>
              </div>
            )}

            {/* Description */}
            {info?.description && (
              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-2">About</h3>
                <p className="text-xs text-gray-400 leading-relaxed line-clamp-6">
                  {info.description.replace(/<[^>]+>/g, "")}
                </p>
              </div>
            )}

            {/* Tags */}
            {info?.tags && info.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {info.tags.map((tag) => (
                  <span key={tag} className="text-[10px] bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Links */}
            <div className="flex flex-wrap gap-2 pt-1">
              {info?.website && (
                <a
                  href={info.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 rounded-lg transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9" />
                  </svg>
                  Website
                </a>
              )}
              {info?.explorer && (
                <a
                  href={info.explorer}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 rounded-lg transition-colors"
                >
                  Explorer
                </a>
              )}
              {info?.twitter && (
                <a
                  href={info.twitter}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 rounded-lg transition-colors"
                >
                  Twitter
                </a>
              )}
            </div>

            {!info && !marketData && (
              <p className="text-sm text-gray-500 text-center py-4">
                No data available for {symbol}. CMC API key may not be configured.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
