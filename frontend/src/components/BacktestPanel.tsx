"use client";

import { useState } from "react";
import { runBacktest } from "@/lib/api";
import type { BacktestResult } from "@/lib/types";

const STRATEGIES = [
  { value: "rsi", label: "RSI" },
  { value: "bollinger", label: "Bollinger Bands" },
  { value: "macd", label: "MACD" },
  { value: "ema_crossover", label: "EMA Crossover" },
  { value: "supertrend", label: "Supertrend" },
  { value: "donchian", label: "Donchian Channel" },
];

const PERIODS = ["3mo", "6mo", "1y", "2y"];

function StatCard({ label, value, suffix, positive }: {
  label: string;
  value: number | null | undefined;
  suffix?: string;
  positive?: boolean | null;
}) {
  if (value == null) return null;
  const colorClass =
    positive === true
      ? "text-green-400"
      : positive === false
        ? "text-red-400"
        : "text-white";

  return (
    <div className="bg-gray-900/50 rounded-lg p-3 text-center">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-lg font-bold ${colorClass}`}>
        {value.toFixed(2)}
        {suffix}
      </div>
    </div>
  );
}

export default function BacktestPanel() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [strategy, setStrategy] = useState("rsi");
  const [period, setPeriod] = useState("1y");
  const [capital, setCapital] = useState(10000);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runBacktest(symbol, strategy, period, capital);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backtest failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800/60 rounded-xl p-6 border border-gray-700/50">
      <h2 className="text-lg font-semibold text-white mb-4">Strategy Backtest</h2>

      <div className="flex flex-wrap gap-2 mb-4">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="BTCUSDT"
          className="bg-gray-900 border border-gray-600 rounded px-3 py-1.5 text-sm text-white w-32"
        />
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          className="bg-gray-900 border border-gray-600 rounded px-3 py-1.5 text-sm text-white"
        >
          {STRATEGIES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
        <div className="flex rounded overflow-hidden border border-gray-600">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-xs font-medium transition ${
                period === p
                  ? "bg-blue-600 text-white"
                  : "bg-gray-900 text-gray-400 hover:text-white"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <input
          type="number"
          value={capital}
          onChange={(e) => setCapital(Number(e.target.value))}
          className="bg-gray-900 border border-gray-600 rounded px-3 py-1.5 text-sm text-white w-28"
          min={100}
        />
        <button
          onClick={handleBacktest}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-1.5 rounded text-sm font-medium transition"
        >
          {loading ? "Running..." : "Run Backtest"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded text-red-300 text-sm mb-4">
          {error}
        </div>
      )}

      {result && !result.error && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              label="Total Return"
              value={result.total_return_pct}
              suffix="%"
              positive={result.total_return_pct > 0}
            />
            <StatCard
              label="Sharpe Ratio"
              value={result.sharpe_ratio}
              positive={result.sharpe_ratio != null ? result.sharpe_ratio > 1 : null}
            />
            <StatCard
              label="Max Drawdown"
              value={result.max_drawdown_pct}
              suffix="%"
              positive={false}
            />
            <StatCard
              label="Win Rate"
              value={result.win_rate != null ? result.win_rate * 100 : null}
              suffix="%"
              positive={result.win_rate != null ? result.win_rate > 0.5 : null}
            />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <StatCard label="Total Trades" value={result.total_trades} />
            <StatCard
              label="Final Equity"
              value={result.final_equity}
              suffix="$"
              positive={result.final_equity > capital}
            />
            <StatCard
              label="Buy & Hold"
              value={result.buy_hold_return_pct}
              suffix="%"
              positive={result.buy_hold_return_pct != null ? result.buy_hold_return_pct > 0 : null}
            />
          </div>
        </div>
      )}

      {!result && !loading && !error && (
        <p className="text-gray-500 text-sm text-center py-8">
          Select a strategy and click Run Backtest to see historical performance.
        </p>
      )}
    </div>
  );
}
