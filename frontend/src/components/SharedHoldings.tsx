"use client";

import { useMemo, useState } from "react";
import type { SharedExchange } from "@/lib/types";

interface Props {
  exchanges: SharedExchange[];
  showCoinAmounts: boolean;
  showTotalValue: boolean;
  showAllocationPct: boolean;
}

type SortKey = "value" | "amount" | "asset" | "allocation";
type SortDir = "asc" | "desc";
type Grouping = "combined" | "exchange";

interface Row {
  asset: string;
  amount: number | null;
  usd_value: number | null;
  allocation_pct: number | null;
  venues: string[];
}

function fmtUsd(val: number | null): string {
  if (val == null) return "—";
  return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtAmount(val: number | null): string {
  if (val == null) return "—";
  if (val >= 1000) return val.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (val >= 1) return val.toFixed(4);
  return val.toFixed(6);
}

function fmtPct(val: number | null): string {
  if (val == null) return "—";
  return `${val.toFixed(2)}%`;
}

/** Sum two values where null means "hidden by the link owner", not zero. */
function addNullable(a: number | null, b: number | null): number | null {
  if (a == null) return b;
  if (b == null) return a;
  return a + b;
}

function combine(exchanges: SharedExchange[]): Row[] {
  const byAsset = new Map<string, Row>();
  for (const ex of exchanges) {
    for (const a of ex.assets) {
      const existing = byAsset.get(a.asset);
      if (existing) {
        existing.amount = addNullable(existing.amount, a.amount);
        existing.usd_value = addNullable(existing.usd_value, a.usd_value);
        existing.allocation_pct = addNullable(existing.allocation_pct, a.allocation_pct);
        if (!existing.venues.includes(ex.exchange_name)) existing.venues.push(ex.exchange_name);
      } else {
        byAsset.set(a.asset, { ...a, venues: [ex.exchange_name] });
      }
    }
  }
  return Array.from(byAsset.values());
}

/** An asset the holding venue has no market for: worth nothing it can realise. */
function isUnpriced(row: Row): boolean {
  return row.usd_value == null || row.usd_value === 0;
}

function sortRows(rows: Row[], key: SortKey, dir: SortDir): Row[] {
  const sign = dir === "asc" ? 1 : -1;
  const byMoney = key === "value" || key === "allocation";
  return [...rows].sort((a, b) => {
    // Unpriced assets sink in either direction when ranking by money. They
    // carry no size information, so ascending order would otherwise open with
    // a wall of them and bury what the viewer came to see.
    if (byMoney && isUnpriced(a) !== isUnpriced(b)) return isUnpriced(a) ? 1 : -1;
    if (key === "asset") return sign * a.asset.localeCompare(b.asset);
    const field = key === "amount" ? "amount" : key === "allocation" ? "allocation_pct" : "usd_value";
    const av = a[field];
    const bv = b[field];
    if (av == null && bv == null) return a.asset.localeCompare(b.asset);
    if (av == null) return 1;
    if (bv == null) return -1;
    return sign * (av - bv);
  });
}

export default function SharedHoldings({
  exchanges,
  showCoinAmounts,
  showTotalValue,
  showAllocationPct,
}: Props) {
  // With values hidden there is nothing to rank by, so fall back to A–Z.
  const [sortKey, setSortKey] = useState<SortKey>(showTotalValue ? "value" : "asset");
  const [sortDir, setSortDir] = useState<SortDir>(showTotalValue ? "desc" : "asc");
  const [grouping, setGrouping] = useState<Grouping>("combined");
  const [search, setSearch] = useState("");
  const [hideUnpriced, setHideUnpriced] = useState(false);

  const multiVenue = exchanges.length > 1;
  // With one exchange there is nothing to combine, and the combined view would
  // drop that exchange's name and total for no gain.
  const effectiveGrouping: Grouping = multiVenue ? grouping : "exchange";

  const groups = useMemo(() => {
    const base =
      effectiveGrouping === "combined"
        ? [{ name: null as string | null, total: null as number | null, rows: combine(exchanges) }]
        : exchanges.map((ex) => ({
            name: ex.exchange_name,
            total: ex.total_usd,
            rows: ex.assets.map((a) => ({ ...a, venues: [ex.exchange_name] })),
          }));

    const needle = search.trim().toLowerCase();
    return base.map((g) => {
      let rows = g.rows;
      if (needle) rows = rows.filter((r) => r.asset.toLowerCase().includes(needle));
      if (hideUnpriced) rows = rows.filter((r) => !isUnpriced(r));
      return { ...g, rows: sortRows(rows, sortKey, sortDir) };
    });
  }, [exchanges, effectiveGrouping, search, hideUnpriced, sortKey, sortDir]);

  const totalRows = useMemo(
    () =>
      effectiveGrouping === "combined"
        ? combine(exchanges).length
        : exchanges.reduce((n, e) => n + e.assets.length, 0),
    [exchanges, effectiveGrouping]
  );
  const shownRows = groups.reduce((n, g) => n + g.rows.length, 0);
  const unpricedCount = useMemo(
    () => combine(exchanges).filter(isUnpriced).length,
    [exchanges]
  );

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      // Names read best A–Z; numbers read best largest-first.
      setSortDir(key === "asset" ? "asc" : "desc");
    }
  }

  function SortHeader({ label, sortKey: key, align = "right" }: { label: string; sortKey: SortKey; align?: "left" | "right" }) {
    const active = sortKey === key;
    return (
      <th
        scope="col"
        aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
        className={`px-5 py-2 font-medium ${align === "left" ? "text-left" : "text-right"}`}
      >
        <button
          type="button"
          onClick={() => toggleSort(key)}
          aria-label={`Sort by ${label}`}
          className={`inline-flex items-center gap-1 hover:text-white transition-colors ${
            active ? "text-blue-400" : "text-gray-500"
          }`}
        >
          {label}
          <span aria-hidden className={active ? "" : "opacity-0"}>{sortDir === "asc" ? "↑" : "↓"}</span>
        </button>
      </th>
    );
  }

  return (
    <section>
      {/* Controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 mb-4 flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search asset…"
          aria-label="Search asset"
          className="flex-1 min-w-[9rem] bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-blue-500"
        />

        {multiVenue && (
          <div className="flex rounded-lg border border-gray-800 overflow-hidden text-xs" role="group" aria-label="Grouping">
            {(["combined", "exchange"] as Grouping[]).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGrouping(g)}
                aria-pressed={grouping === g}
                className={`px-3 py-2 transition-colors ${
                  grouping === g ? "bg-blue-600 text-white" : "bg-gray-950 text-gray-400 hover:text-white"
                }`}
              >
                {g === "combined" ? "All holdings" : "By exchange"}
              </button>
            ))}
          </div>
        )}

        {showTotalValue && unpricedCount > 0 && (
          <button
            type="button"
            onClick={() => setHideUnpriced(!hideUnpriced)}
            aria-pressed={hideUnpriced}
            className={`px-3 py-2 rounded-lg border text-xs transition-colors ${
              hideUnpriced
                ? "bg-blue-600 border-blue-600 text-white"
                : "bg-gray-950 border-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            Hide unpriced ({unpricedCount})
          </button>
        )}
      </div>

      <p className="text-xs text-gray-600 mb-3">
        {shownRows === totalRows ? `${totalRows} assets` : `${shownRows} of ${totalRows} assets`}
      </p>

      <div className="space-y-4">
        {groups.map((group, gi) => (
          <div key={gi} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            {group.name !== null && (
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
                <h2 className="font-semibold text-white">{group.name}</h2>
                {group.total != null && (
                  <span className="text-sm text-gray-300">{fmtUsd(group.total)}</span>
                )}
              </div>
            )}

            {group.rows.length === 0 ? (
              <p className="text-sm text-gray-600 px-5 py-4">
                {search ? `No assets matching “${search}”` : "No assets"}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs border-b border-gray-800">
                      <SortHeader label="Asset" sortKey="asset" align="left" />
                      {showCoinAmounts && <SortHeader label="Amount" sortKey="amount" />}
                      {showTotalValue && <SortHeader label="Value" sortKey="value" />}
                      {showAllocationPct && <SortHeader label="Allocation" sortKey="allocation" />}
                    </tr>
                  </thead>
                  <tbody>
                    {group.rows.map((row) => {
                      const unpriced = showTotalValue && isUnpriced(row);
                      return (
                        <tr
                          key={row.asset}
                          className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30"
                        >
                          <td className="px-5 py-3 font-medium text-white">
                            <span className="flex items-center gap-1.5 flex-wrap">
                              {row.asset}
                              {unpriced && (
                                <span className="text-[10px] text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded-sm font-normal">
                                  no price
                                </span>
                              )}
                              {effectiveGrouping === "combined" && row.venues.length > 1 && (
                                <span className="text-[10px] text-gray-500 font-normal">
                                  {row.venues.length} exchanges
                                </span>
                              )}
                            </span>
                          </td>
                          {showCoinAmounts && (
                            <td className="px-5 py-3 text-right text-gray-300">{fmtAmount(row.amount)}</td>
                          )}
                          {showTotalValue && (
                            <td className="px-5 py-3 text-right text-gray-300">{fmtUsd(row.usd_value)}</td>
                          )}
                          {showAllocationPct && (
                            <td className="px-5 py-3 text-right text-gray-400">{fmtPct(row.allocation_pct)}</td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
