"use client";

import { useMemo, useState } from "react";
import type { SharedExchange } from "@/lib/types";

interface Props {
  exchanges: SharedExchange[];
  showCoinAmounts: boolean;
  showTotalValue: boolean;
  showAllocationPct: boolean;
  showAvgBuyPrice: boolean;
}

type SortKey = "value" | "amount" | "asset" | "allocation" | "avgBuyPrice";
type SortDir = "asc" | "desc";
type Grouping = "combined" | "exchange";

interface Row {
  asset: string;
  amount: number | null;
  usd_value: number | null;
  allocation_pct: number | null;
  avg_buy_price: number | null;
  venues: string[];
}

function fmtUsd(val: number | null): string {
  if (val == null) return "—";
  return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Adaptive precision so a sub-cent avg price doesn't round away to $0.00. */
function fmtAvgPrice(val: number | null): string {
  if (val == null) return "—";
  if (val >= 1) return `$${val.toFixed(2)}`;
  if (val >= 0.01) return `$${val.toFixed(4)}`;
  return `$${val.toFixed(6)}`;
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
  // Average buy price isn't additive across venues — it needs a weighted
  // average (weight by amount; equal weight when amounts are hidden/absent),
  // tracked separately and folded in once every venue has been seen.
  const avgWeight = new Map<string, { num: number; den: number; any: boolean }>();

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

      if (a.avg_buy_price != null) {
        const weight = a.amount != null && a.amount > 0 ? a.amount : 1;
        const acc = avgWeight.get(a.asset) ?? { num: 0, den: 0, any: false };
        acc.num += a.avg_buy_price * weight;
        acc.den += weight;
        acc.any = true;
        avgWeight.set(a.asset, acc);
      }
    }
  }

  byAsset.forEach((row, asset) => {
    const acc = avgWeight.get(asset);
    row.avg_buy_price = acc && acc.any && acc.den > 0 ? acc.num / acc.den : null;
  });

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
    const field =
      key === "amount"
        ? "amount"
        : key === "allocation"
          ? "allocation_pct"
          : key === "avgBuyPrice"
            ? "avg_buy_price"
            : "usd_value";
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
  showAvgBuyPrice,
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

  function SortHeader({
    label,
    sortKey: key,
    align = "right",
    narrowHidden = false,
  }: {
    label: string;
    sortKey: SortKey;
    align?: "left" | "right";
    narrowHidden?: boolean;
  }) {
    const active = sortKey === key;
    return (
      <th
        scope="col"
        aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
        className={`px-4 sm:px-5 py-2 font-medium ${align === "left" ? "text-left" : "text-right"} ${
          narrowHidden ? "hidden sm:table-cell" : ""
        }`}
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

  // Columns folded away on a phone lose their header button, so the sort keys
  // they carry are offered here instead. Kept out of the accessibility tree on
  // wide screens so the headers stay the single set of sort controls.
  const sortOptions: { key: SortKey; label: string }[] = [
    { key: "asset", label: "Name" },
    ...(showCoinAmounts ? [{ key: "amount" as SortKey, label: "Amount" }] : []),
    ...(showTotalValue ? [{ key: "value" as SortKey, label: "Value" }] : []),
    ...(showAllocationPct ? [{ key: "allocation" as SortKey, label: "Allocation" }] : []),
    ...(showAvgBuyPrice ? [{ key: "avgBuyPrice" as SortKey, label: "Avg buy" }] : []),
  ];

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

      <div className="flex items-center justify-between gap-2 mb-3">
        <p className="text-xs text-gray-600">
          {shownRows === totalRows ? `${totalRows} assets` : `${shownRows} of ${totalRows} assets`}
        </p>

        {sortOptions.length > 1 && (
          <div className="sm:hidden flex items-center gap-1" aria-hidden={false}>
            <label htmlFor="sort-by" className="sr-only">
              Sort by
            </label>
            <select
              id="sort-by"
              value={sortKey}
              onChange={(e) => toggleSort(e.target.value as SortKey)}
              className="bg-gray-950 border border-gray-800 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
            >
              {sortOptions.map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setSortDir(sortDir === "asc" ? "desc" : "asc")}
              aria-label={sortDir === "asc" ? "Sort descending" : "Sort ascending"}
              className="px-2 py-1.5 rounded-lg border border-gray-800 bg-gray-950 text-xs text-gray-300"
            >
              {sortDir === "asc" ? "↑" : "↓"}
            </button>
          </div>
        )}
      </div>

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
              <p className="text-xs sm:text-sm text-gray-600 px-4 sm:px-5 py-4">
                {search ? `No assets matching “${search}”` : "No assets"}
              </p>
            ) : (
              <table className="w-full text-xs sm:text-sm">
                <thead>
                  {/* Amount, Allocation and Avg buy collapse into the two remaining
                      cells on a phone rather than pushing the table off-screen. */}
                  <tr className="text-[11px] sm:text-xs border-b border-gray-800">
                    <SortHeader label="Asset" sortKey="asset" align="left" />
                    {showCoinAmounts && <SortHeader label="Amount" sortKey="amount" narrowHidden />}
                    {showTotalValue && <SortHeader label="Value" sortKey="value" />}
                    {showAllocationPct && <SortHeader label="Allocation" sortKey="allocation" narrowHidden={showTotalValue} />}
                    {showAvgBuyPrice && <SortHeader label="Avg buy" sortKey="avgBuyPrice" narrowHidden />}
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
                        <td className="px-4 sm:px-5 py-2.5 sm:py-3 font-medium text-white">
                          <span className="flex items-center gap-1.5 flex-wrap">
                            {/* The badges and the folded amount share this cell,
                                so the symbol is tagged for tests to address. */}
                            <span data-testid="asset-symbol">{row.asset}</span>
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
                          {(showCoinAmounts || showAvgBuyPrice) && (
                            <span className="sm:hidden block text-[11px] text-gray-500 tabular-nums">
                              {[
                                showCoinAmounts ? fmtAmount(row.amount) : null,
                                showAvgBuyPrice ? `avg ${fmtAvgPrice(row.avg_buy_price)}` : null,
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </span>
                          )}
                        </td>
                        {showCoinAmounts && (
                          <td className="hidden sm:table-cell px-5 py-3 text-right text-gray-300 tabular-nums">
                            {fmtAmount(row.amount)}
                          </td>
                        )}
                        {showTotalValue && (
                          <td className="px-4 sm:px-5 py-2.5 sm:py-3 text-right text-gray-300 tabular-nums">
                            {fmtUsd(row.usd_value)}
                            {showAllocationPct && (
                              <span className="sm:hidden block text-[11px] text-gray-500">
                                {fmtPct(row.allocation_pct)}
                              </span>
                            )}
                          </td>
                        )}
                        {showAllocationPct && (
                          <td
                            className={`px-4 sm:px-5 py-2.5 sm:py-3 text-right text-gray-400 tabular-nums ${
                              showTotalValue ? "hidden sm:table-cell" : ""
                            }`}
                          >
                            {fmtPct(row.allocation_pct)}
                          </td>
                        )}
                        {showAvgBuyPrice && (
                          <td className="hidden sm:table-cell px-4 sm:px-5 py-2.5 sm:py-3 text-right text-gray-400 tabular-nums">
                            {fmtAvgPrice(row.avg_buy_price)}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
