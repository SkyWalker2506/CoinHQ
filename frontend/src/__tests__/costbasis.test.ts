import { describe, it, expect } from "vitest";
import { formatUnitPrice, mergeCostBasis } from "@/lib/costBasis";
import type { CostBasisResponse } from "@/lib/types";

const response = (profileId: number, exchanges: CostBasisResponse["exchanges"]): CostBasisResponse => ({
  profile_id: profileId,
  computed_at: "2026-09-27T12:00:00Z",
  exchanges,
});

describe("formatUnitPrice", () => {
  it("groups thousands like every other price on the page", () => {
    expect(formatUnitPrice(49164.2023)).toBe("$49,164.20");
  });

  it("keeps enough decimals that small coins do not read as $0.00", () => {
    expect(formatUnitPrice(0.2244)).toBe("$0.2244");
    expect(formatUnitPrice(0.0000654)).toBe("$0.000065");
  });
});

describe("mergeCostBasis", () => {
  it("returns nothing for no profiles and the response itself for one", () => {
    const single = response(1, []);
    expect(mergeCostBasis([])).toBeUndefined();
    expect(mergeCostBasis([single])).toBe(single);
  });

  it("weights a shared (exchange, asset) by how much each profile bought", () => {
    const merged = mergeCostBasis([
      response(1, [{ exchange: "gateio", supported: true, assets: [
        { asset: "UNI", avg_buy_price: 4, bought_qty: 30, coverage: "full" },
      ] }]),
      response(2, [{ exchange: "gateio", supported: true, assets: [
        { asset: "UNI", avg_buy_price: 8, bought_qty: 10, coverage: "full" },
      ] }]),
    ]);
    const uni = merged!.exchanges[0].assets[0];
    expect(uni.avg_buy_price).toBeCloseTo(5); // (4*30 + 8*10) / 40
    expect(uni.bought_qty).toBe(40);
    expect(uni.coverage).toBe("full");
  });

  it("is only full when every contributing profile's history was", () => {
    const merged = mergeCostBasis([
      response(1, [{ exchange: "gateio", supported: true, assets: [
        { asset: "UNI", avg_buy_price: 4, bought_qty: 10, coverage: "full" },
      ] }]),
      response(2, [{ exchange: "gateio", supported: true, assets: [
        { asset: "UNI", avg_buy_price: null, bought_qty: 0, coverage: "none" },
      ] }]),
    ]);
    const uni = merged!.exchanges[0].assets[0];
    expect(uni.avg_buy_price).toBe(4); // the unpriced side adds no weight
    expect(uni.coverage).toBe("partial");
  });

  it("keeps a venue supported if any profile could read it", () => {
    const merged = mergeCostBasis([
      response(1, [{ exchange: "binance", supported: false, assets: [] }]),
      response(2, [{ exchange: "binance", supported: true, assets: [
        { asset: "BTC", avg_buy_price: 60000, bought_qty: 1, coverage: "full" },
      ] }]),
    ]);
    expect(merged!.exchanges[0].supported).toBe(true);
    expect(merged!.exchanges[0].assets).toHaveLength(1);
  });
});
