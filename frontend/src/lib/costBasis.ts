import type { CostBasisAsset, CostBasisExchange, CostBasisResponse } from "./types";

/**
 * USD price of one coin, with enough decimals that a sub-cent altcoin does not
 * round to $0.00, and thousands separators like every other price on the page.
 */
export function formatUnitPrice(value: number): string {
  const decimals = value >= 1 ? 2 : value >= 0.01 ? 4 : 6;
  return `$${value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

/**
 * Fold several profiles' cost bases into one, for the "All Profiles" view.
 *
 * That view lists every profile's exchanges together, so the same
 * (exchange, asset) pair can appear once per profile. Those entries merge into
 * one average weighted by how much each profile bought; coverage is only
 * "full" when every contributing profile's history was.
 */
export function mergeCostBasis(responses: CostBasisResponse[]): CostBasisResponse | undefined {
  if (responses.length === 0) return undefined;
  if (responses.length === 1) return responses[0];

  const exchanges = new Map<string, { supported: boolean; assets: Map<string, CostBasisAsset[]> }>();
  for (const response of responses) {
    for (const ex of response.exchanges) {
      const slot = exchanges.get(ex.exchange) ?? { supported: false, assets: new Map() };
      slot.supported = slot.supported || ex.supported;
      for (const asset of ex.assets) {
        slot.assets.set(asset.asset, [...(slot.assets.get(asset.asset) ?? []), asset]);
      }
      exchanges.set(ex.exchange, slot);
    }
  }

  const merged: CostBasisExchange[] = Array.from(exchanges, ([exchange, slot]) => ({
    exchange,
    supported: slot.supported,
    assets: Array.from(slot.assets, ([asset, entries]) => mergeAsset(asset, entries)),
  }));

  return {
    profile_id: responses[0].profile_id,
    computed_at: responses[0].computed_at,
    exchanges: merged,
  };
}

function mergeAsset(asset: string, entries: CostBasisAsset[]): CostBasisAsset {
  if (entries.length === 1) return entries[0];
  const priced = entries.filter((e) => e.avg_buy_price != null && e.bought_qty > 0);
  const boughtQty = priced.reduce((sum, e) => sum + e.bought_qty, 0);
  if (priced.length === 0 || boughtQty <= 0) {
    return { asset, avg_buy_price: null, bought_qty: 0, coverage: "none" };
  }
  const cost = priced.reduce((sum, e) => sum + (e.avg_buy_price as number) * e.bought_qty, 0);
  return {
    asset,
    avg_buy_price: cost / boughtQty,
    bought_qty: boughtQty,
    coverage: entries.every((e) => e.coverage === "full") ? "full" : "partial",
  };
}
