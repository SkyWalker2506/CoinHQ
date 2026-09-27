import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { SharedExchange } from "@/lib/types";

import SharedHoldings from "@/components/SharedHoldings";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const EXCHANGES: SharedExchange[] = [
  {
    exchange_name: "gateio",
    total_usd: 1740.11,
    assets: [
      { asset: "UNI", amount: 13.47, usd_value: 56.8, allocation_pct: 3.2, avg_buy_price: 5.12 },
      { asset: "ALPACA", amount: 1894.26, usd_value: 0, allocation_pct: 0, avg_buy_price: null },
      { asset: "DOGS", amount: 1163916.88, usd_value: 40.07, allocation_pct: 2.3, avg_buy_price: 0.00004 },
    ],
  },
  {
    exchange_name: "binance",
    total_usd: 500,
    assets: [
      { asset: "BTC", amount: 0.01, usd_value: 450, allocation_pct: 25.9, avg_buy_price: 40000 },
      { asset: "UNI", amount: 5, usd_value: 21.1, allocation_pct: 1.2, avg_buy_price: 4 },
    ],
  },
];

function renderHoldings(props: Partial<React.ComponentProps<typeof SharedHoldings>> = {}) {
  return render(
    <SharedHoldings
      exchanges={EXCHANGES}
      showCoinAmounts
      showTotalValue
      showAllocationPct
      showAvgBuyPrice={false}
      {...props}
    />
  );
}

/** Asset symbols in render order. The cell also carries badges and, on narrow
 *  screens, the folded amount, so the symbol itself is addressed directly. */
function assetOrder(): string[] {
  return screen.getAllByTestId("asset-symbol").map((el) => el.textContent ?? "");
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("SharedHoldings", () => {
  it("defaults to combined holdings sorted by value, largest first", () => {
    renderHoldings();
    // UNI is merged across both venues: 56.8 + 21.1 = 77.9, above DOGS.
    expect(assetOrder()).toEqual(["BTC", "UNI", "DOGS", "ALPACA"]);
    expect(screen.getByText("$77.90")).toBeInTheDocument();
    expect(screen.getByText("2 exchanges")).toBeInTheDocument();
  });

  it("reverses direction when the active sort header is clicked again", async () => {
    const user = userEvent.setup();
    renderHoldings();

    await user.click(screen.getByRole("button", { name: "Sort by Value" }));

    // Ascending by value — but unpriced assets stay last in either direction.
    expect(assetOrder()).toEqual(["DOGS", "UNI", "BTC", "ALPACA"]);
  });

  it("sorts by asset name A–Z", async () => {
    const user = userEvent.setup();
    renderHoldings();

    await user.click(screen.getByRole("button", { name: "Sort by Asset" }));

    expect(assetOrder()).toEqual(["ALPACA", "BTC", "DOGS", "UNI"]);
  });

  it("sorts by amount", async () => {
    const user = userEvent.setup();
    renderHoldings();

    await user.click(screen.getByRole("button", { name: "Sort by Amount" }));

    expect(assetOrder()).toEqual(["DOGS", "ALPACA", "UNI", "BTC"]);
  });

  it("filters by search text", async () => {
    const user = userEvent.setup();
    renderHoldings();

    await user.type(screen.getByRole("searchbox", { name: "Search asset" }), "do");

    expect(assetOrder()).toEqual(["DOGS"]);
    expect(screen.getByText("1 of 4 assets")).toBeInTheDocument();
  });

  it("tells the viewer when a search matches nothing", async () => {
    const user = userEvent.setup();
    renderHoldings();

    await user.type(screen.getByRole("searchbox", { name: "Search asset" }), "zzz");

    expect(screen.getByText(/No assets matching/)).toBeInTheDocument();
  });

  it("hides unpriced assets on request", async () => {
    const user = userEvent.setup();
    renderHoldings();

    await user.click(screen.getByRole("button", { name: /Hide unpriced \(1\)/ }));

    expect(assetOrder()).toEqual(["BTC", "UNI", "DOGS"]);
  });

  it("splits by exchange and keeps each venue's own total", async () => {
    const user = userEvent.setup();
    renderHoldings();

    await user.click(screen.getByRole("button", { name: "By exchange" }));

    expect(screen.getByRole("heading", { name: "gateio" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "binance" })).toBeInTheDocument();
    expect(screen.getByText("$1,740.11")).toBeInTheDocument();
    // UNI is no longer merged — it appears once per venue.
    expect(assetOrder().filter((a) => a === "UNI")).toHaveLength(2);
  });

  it("offers no grouping toggle for a single-exchange portfolio, and keeps its header", () => {
    renderHoldings({ exchanges: [EXCHANGES[0]] });

    expect(screen.queryByRole("button", { name: "By exchange" })).not.toBeInTheDocument();
    // Nothing to combine, so the venue's name and total must not be dropped.
    expect(screen.getByRole("heading", { name: "gateio" })).toBeInTheDocument();
    expect(screen.getByText("$1,740.11")).toBeInTheDocument();
  });

  it("drops hidden columns and ranks A–Z when the owner hides values", () => {
    renderHoldings({ showTotalValue: false, showAllocationPct: false });

    expect(screen.queryByRole("button", { name: "Sort by Value" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sort by Allocation" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Hide unpriced/ })).not.toBeInTheDocument();
    expect(assetOrder()).toEqual(["ALPACA", "BTC", "DOGS", "UNI"]);
  });

  describe("average buy price", () => {
    it("is hidden entirely when the owner turns the flag off", () => {
      renderHoldings({ showAvgBuyPrice: false });

      expect(screen.queryByRole("button", { name: "Sort by Avg buy" })).not.toBeInTheDocument();
      expect(screen.queryByText("$4.82")).not.toBeInTheDocument();
    });

    it("shows an Avg buy column when the owner turns the flag on", () => {
      renderHoldings({ showAvgBuyPrice: true });

      expect(screen.getByRole("button", { name: "Sort by Avg buy" })).toBeInTheDocument();
    });

    it("weights the combined average by amount across venues", () => {
      renderHoldings({ showAvgBuyPrice: true });

      // UNI: gateio 13.47 @ $5.12, binance 5 @ $4 → (13.47*5.12 + 5*4) / 18.47 ≈ $4.82
      expect(screen.getByText("$4.82")).toBeInTheDocument();
    });

    it("keeps each venue's own average when split by exchange", async () => {
      const user = userEvent.setup();
      renderHoldings({ showAvgBuyPrice: true });

      await user.click(screen.getByRole("button", { name: "By exchange" }));

      expect(screen.getByText("$5.12")).toBeInTheDocument();
      expect(screen.getByText("$4.00")).toBeInTheDocument();
      expect(screen.queryByText("$4.82")).not.toBeInTheDocument();
    });

    it("uses adaptive precision so a sub-cent average doesn't round to $0.00", () => {
      renderHoldings({ showAvgBuyPrice: true });

      expect(screen.getByText("$0.000040")).toBeInTheDocument();
    });

    it("shows — when an asset's average buy price is unknown", () => {
      renderHoldings({ showAvgBuyPrice: true, exchanges: [EXCHANGES[0]] });

      // ALPACA has no avg_buy_price on its only venue.
      const row = screen.getByText("ALPACA").closest("tr");
      expect(row).not.toBeNull();
      expect(row!.textContent).toContain("—");
    });
  });
});
