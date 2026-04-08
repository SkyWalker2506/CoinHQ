"use client";

import { useState } from "react";
import { getCoinAnalysis } from "@/lib/api";
import type { CoinAnalysis } from "@/lib/types";

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"];

function RecBadge({ rec }: { rec: string }) {
  const colors: Record<string, string> = {
    STRONG_BUY: "bg-green-600 text-white",
    BUY: "bg-green-500/80 text-white",
    NEUTRAL: "bg-yellow-500/80 text-black",
    SELL: "bg-red-500/80 text-white",
    STRONG_SELL: "bg-red-700 text-white",
  };
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-bold ${colors[rec] ?? "bg-gray-600 text-white"}`}>
      {rec.replace("_", " ")}
    </span>
  );
}

function IndicatorRow({ label, value, unit }: { label: string; value: number | null | undefined; unit?: string }) {
  if (value == null) return null;
  return (
    <div className="flex justify-between py-1 border-b border-gray-700/50">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className="text-white text-sm font-mono">
        {typeof value === "number" ? value.toFixed(2) : value}
        {unit && <span className="text-gray-500 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export default function TechnicalAnalysis({ symbol: initialSymbol }: { symbol?: string }) {
  const [symbol, setSymbol] = useState(initialSymbol ?? "BTCUSDT");
  const [exchange, setExchange] = useState("BINANCE");
  const [interval, setInterval] = useState("1h");
  const [analysis, setAnalysis] = useState<CoinAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCoinAnalysis(symbol, exchange, interval);
      setAnalysis(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800/60 rounded-xl p-6 border border-gray-700/50">
      <h2 className="text-lg font-semibold text-white mb-4">Technical Analysis</h2>

      {/* Controls */}
      <div className="flex flex-wrap gap-2 mb-4">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="BTCUSDT"
          className="bg-gray-900 border border-gray-600 rounded px-3 py-1.5 text-sm text-white w-32"
        />
        <select
          value={exchange}
          onChange={(e) => setExchange(e.target.value)}
          className="bg-gray-900 border border-gray-600 rounded px-3 py-1.5 text-sm text-white"
        >
          <option value="BINANCE">Binance</option>
          <option value="BYBIT">Bybit</option>
          <option value="KUCOIN">KuCoin</option>
          <option value="COINBASE">Coinbase</option>
          <option value="OKX">OKX</option>
        </select>
        <div className="flex rounded overflow-hidden border border-gray-600">
          {INTERVALS.map((tf) => (
            <button
              key={tf}
              onClick={() => setInterval(tf)}
              className={`px-2 py-1.5 text-xs font-medium transition ${
                interval === tf
                  ? "bg-blue-600 text-white"
                  : "bg-gray-900 text-gray-400 hover:text-white"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
        <button
          onClick={fetchAnalysis}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-1.5 rounded text-sm font-medium transition"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded text-red-300 text-sm mb-4">
          {error}
        </div>
      )}

      {analysis && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="flex items-center gap-4 p-4 bg-gray-900/50 rounded-lg">
            <div>
              <div className="text-sm text-gray-400 mb-1">
                {analysis.symbol} @ {analysis.exchange}
              </div>
              <div className="text-2xl font-bold text-white">
                ${analysis.price.close?.toLocaleString(undefined, { maximumFractionDigits: 6 })}
              </div>
              {analysis.price.change != null && (
                <span className={`text-sm ${analysis.price.change >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {analysis.price.change >= 0 ? "+" : ""}
                  {analysis.price.change.toFixed(2)}%
                </span>
              )}
            </div>
            <div className="ml-auto text-right">
              <div className="text-xs text-gray-400 mb-1">Recommendation</div>
              <RecBadge rec={analysis.summary.recommendation} />
              <div className="mt-2 flex gap-2 text-xs">
                <span className="text-green-400">{analysis.summary.buy} Buy</span>
                <span className="text-gray-400">{analysis.summary.neutral} Neutral</span>
                <span className="text-red-400">{analysis.summary.sell} Sell</span>
              </div>
            </div>
          </div>

          {/* Indicators Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Oscillators */}
            <div className="bg-gray-900/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Oscillators</h3>
              <IndicatorRow label="RSI (14)" value={analysis.indicators.rsi} />
              <IndicatorRow label="Stoch %K" value={analysis.indicators.stoch_k} />
              <IndicatorRow label="Stoch %D" value={analysis.indicators.stoch_d} />
              <IndicatorRow label="CCI (20)" value={analysis.indicators.cci} />
              <IndicatorRow label="ADX" value={analysis.indicators.adx} />
              <IndicatorRow label="ATR" value={analysis.indicators.atr} />
            </div>

            {/* MACD & Bollinger */}
            <div className="bg-gray-900/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">MACD & Bollinger</h3>
              <IndicatorRow label="MACD" value={analysis.indicators.macd.macd} />
              <IndicatorRow label="Signal" value={analysis.indicators.macd.signal} />
              <IndicatorRow label="BB Upper" value={analysis.indicators.bollinger.upper} />
              <IndicatorRow label="BB Basis" value={analysis.indicators.bollinger.basis} />
              <IndicatorRow label="BB Lower" value={analysis.indicators.bollinger.lower} />
            </div>

            {/* Moving Averages */}
            <div className="bg-gray-900/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Moving Averages</h3>
              <IndicatorRow label="EMA 10" value={analysis.indicators.ema.ema10} />
              <IndicatorRow label="EMA 20" value={analysis.indicators.ema.ema20} />
              <IndicatorRow label="EMA 50" value={analysis.indicators.ema.ema50} />
              <IndicatorRow label="EMA 100" value={analysis.indicators.ema.ema100} />
              <IndicatorRow label="EMA 200" value={analysis.indicators.ema.ema200} />
            </div>
          </div>
        </div>
      )}

      {!analysis && !loading && !error && (
        <p className="text-gray-500 text-sm text-center py-8">
          Enter a symbol and click Analyze to see technical indicators.
        </p>
      )}
    </div>
  );
}
