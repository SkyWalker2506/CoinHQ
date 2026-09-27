import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CostBasisResponse, ExchangeBalance } from "@/lib/types";

import ExchangeList from "@/components/ExchangeList";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const EXCHANGES: ExchangeBalance[] = [
  {
    exchange: "gateio",
    total_usd: 101.2,
    balances: [
      { asset: "UNI", free: 10, locked: 0, total: 10, usd_value: 51.2 },
      { asset: "DOGS", free: 100, locked: 0, total: 100, usd_value: 40 },
      { asset: "XYZ", free: 1, locked: 0, total: 1, usd_value: 10 },
    ],
  },
  {
    exchange: "binance",
    total_usd: 450,
    balances: [{ asset: "BTC", free: 0.01, locked: 0, total: 0.01, usd_value: 450 }],
  },
];

const COST_BASIS: CostBasisResponse = {
  profile_id: 1,
  computed_at: "2026-09-27T12:00:00Z",
  exchanges: [
    {
      exchange: "gateio",
      supported: true,
      assets: [
        // current price 51.2/10 = 5.12 vs avg 4 → +28.0%
        { asset: "UNI", avg_buy_price: 4, bought_qty: 10, coverage: "full" },
        // current price 40/100 = 0.4 vs avg 0.5 → -20.0%
        { asset: "DOGS", avg_buy_price: 0.5, bought_qty: 100, coverage: "partial" },
        { asset: "XYZ", avg_buy_price: null, bought_qty: 0, coverage: "none" },
      ],
    },
    {
      exchange: "binance",
      supported: false,
      assets: [{ asset: "BTC", avg_buy_price: 30000, bought_qty: 0.01, coverage: "full" }],
    },
  ],
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ExchangeList — average buy price", () => {
  it("renders nothing extra while cost basis hasn't loaded yet", () => {
    render(<ExchangeList exchanges={EXCHANGES} />);

    expect(screen.queryByText(/^Avg /)).not.toBeInTheDocument();
    expect(screen.queryByText(/^\+\d/)).not.toBeInTheDocument();
  });

  it("shows the average buy price and unrealised gain in green for full coverage", () => {
    render(<ExchangeList exchanges={EXCHANGES} costBasis={COST_BASIS} />);

    expect(screen.getByText("Avg $4.00")).toBeInTheDocument();
    const pct = screen.getByText("+28.0%");
    expect(pct).toBeInTheDocument();
    expect(pct.className).toMatch(/green/);
  });

  it("marks partial coverage with a ~ prefix, a tooltip, and a red loss percentage", () => {
    render(<ExchangeList exchanges={EXCHANGES} costBasis={COST_BASIS} />);

    const avgLine = screen.getByText("~Avg $0.5000");
    expect(avgLine).toBeInTheDocument();
    expect(avgLine).toHaveAttribute(
      "title",
      "Partial history: some of this holding came from deposits or older trades"
    );

    const pct = screen.getByText("-20.0%");
    expect(pct.className).toMatch(/red/);
  });

  it("shows nothing for coverage 'none'", () => {
    render(<ExchangeList exchanges={EXCHANGES} costBasis={COST_BASIS} />);

    // XYZ has coverage "none" — no avg line, no percentage for it.
    const xyzRow = screen.getByText("XYZ").closest("div.flex.items-center.justify-between");
    expect(xyzRow?.textContent).not.toMatch(/Avg \$/);
  });

  it("shows nothing for an unsupported exchange even if it has cost-basis rows", () => {
    render(<ExchangeList exchanges={EXCHANGES} costBasis={COST_BASIS} />);

    // BTC lives on binance, which is marked unsupported.
    const btcRow = screen.getByText("BTC").closest("div.flex.items-center.justify-between");
    expect(btcRow?.textContent).not.toMatch(/Avg \$/);
  });
});
