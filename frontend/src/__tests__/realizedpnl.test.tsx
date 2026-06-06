import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { PnlResponse } from "@/lib/types";

// ── Hook mock ─────────────────────────────────────────────────────────────────

let mockHookReturn: {
  pnl: PnlResponse | undefined;
  error: Error | undefined;
  isLoading: boolean;
} = { pnl: undefined, error: undefined, isLoading: false };

vi.mock("@/hooks/usePortfolio", () => ({
  useProfilePnl: () => mockHookReturn,
}));

// Import after mocking
import RealizedPnL from "@/components/RealizedPnL";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makePnl = (overrides: Partial<PnlResponse> = {}): PnlResponse => ({
  total_realized_pnl_usd: 1500.0,
  assets: [
    {
      base_asset: "BTC",
      current_qty: 1.5,
      avg_cost: 15000.0,
      realized_pnl_usd: 1500.0,
      total_bought_usd: 30000.0,
      total_sold_usd: 9000.0,
      buy_count: 2,
      sell_count: 1,
    },
  ],
  ...overrides,
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("RealizedPnL", () => {
  beforeEach(() => {
    mockHookReturn = { pnl: undefined, error: undefined, isLoading: false };
  });

  it("renders total and per-asset rows from mocked data", () => {
    mockHookReturn = { pnl: makePnl(), error: undefined, isLoading: false };

    render(<RealizedPnL profileId={1} />);

    // Total P&L shown (appears in header + per-asset row)
    expect(screen.getAllByText(/\+\$1,500\.00/).length).toBeGreaterThanOrEqual(1);
    // Asset row
    expect(screen.getByText("BTC")).toBeInTheDocument();
    // Avg cost
    expect(screen.getByText("$15,000.00")).toBeInTheDocument();
    // Buy/sell count
    expect(screen.getByText("2B / 1S")).toBeInTheDocument();
  });

  it("styles positive P&L with green", () => {
    mockHookReturn = { pnl: makePnl({ total_realized_pnl_usd: 1500 }), error: undefined, isLoading: false };

    render(<RealizedPnL profileId={1} />);

    // The total amount element should have green class
    const totalEl = screen.getByLabelText(/total realized p&l/i);
    expect(totalEl.className).toMatch(/green/);
  });

  it("styles negative P&L with red", () => {
    const negativePnl = makePnl({
      total_realized_pnl_usd: -500,
      assets: [
        {
          base_asset: "ETH",
          current_qty: 2,
          avg_cost: 2000,
          realized_pnl_usd: -500,
          total_bought_usd: 4000,
          total_sold_usd: 1000,
          buy_count: 1,
          sell_count: 1,
        },
      ],
    });
    mockHookReturn = { pnl: negativePnl, error: undefined, isLoading: false };

    render(<RealizedPnL profileId={1} />);

    const totalEl = screen.getByLabelText(/total realized p&l/i);
    expect(totalEl.className).toMatch(/red/);
    // Per-asset pnl cell also red
    const pnlCells = screen.getAllByText("-$500.00");
    expect(pnlCells.some((el) => el.className.match(/red/))).toBe(true);
  });

  it("shows '—' when avg_cost is null", () => {
    const pnl = makePnl({
      assets: [
        {
          base_asset: "SOL",
          current_qty: 0,
          avg_cost: null,
          realized_pnl_usd: 200,
          total_bought_usd: 500,
          total_sold_usd: 700,
          buy_count: 1,
          sell_count: 1,
        },
      ],
    });
    mockHookReturn = { pnl, error: undefined, isLoading: false };

    render(<RealizedPnL profileId={1} />);

    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows empty state when assets list is empty", () => {
    mockHookReturn = {
      pnl: { total_realized_pnl_usd: 0, assets: [] },
      error: undefined,
      isLoading: false,
    };

    render(<RealizedPnL profileId={1} />);

    expect(screen.getByText(/no completed trades yet/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows error alert when hook returns an error", () => {
    mockHookReturn = {
      pnl: undefined,
      error: new Error("Server error"),
      isLoading: false,
    };

    render(<RealizedPnL profileId={1} />);

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toMatch(/server error/i);
  });

  it("shows the 'CoinHQ trades only' disclaimer caption", () => {
    mockHookReturn = { pnl: makePnl(), error: undefined, isLoading: false };

    render(<RealizedPnL profileId={1} />);

    expect(screen.getByText(/coinHQ trades only/i)).toBeInTheDocument();
    expect(screen.getByText(/excludes positions traded directly on exchanges/i)).toBeInTheDocument();
  });
});
