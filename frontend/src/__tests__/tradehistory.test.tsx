import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { TradeOrder } from "@/lib/types";

// ── SWR mock ─────────────────────────────────────────────────────────────────
// We control the hook's return value per-test via this variable.
let mockHookReturn: {
  trades: TradeOrder[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
} = { trades: undefined, error: undefined, isLoading: false };

vi.mock("@/hooks/usePortfolio", () => ({
  useTradeHistory: () => mockHookReturn,
}));

// Import after mocking
import TradeHistory from "@/components/TradeHistory";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makeTrade = (overrides: Partial<TradeOrder> = {}): TradeOrder => ({
  id: 1,
  exchange: "binance",
  symbol: "BTCUSDT",
  base_asset: "BTC",
  side: "buy",
  usd_value: 250.5,
  amount: 0.005,
  actor: "owner",
  status: "filled",
  exchange_order_id: "EX-001",
  error: null,
  created_at: "2026-06-06T10:00:00.000Z",
  ...overrides,
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("TradeHistory", () => {
  beforeEach(() => {
    mockHookReturn = { trades: undefined, error: undefined, isLoading: false };
  });

  it("renders trade rows from a mocked list", () => {
    const trades = [
      makeTrade({ id: 1, base_asset: "BTC", usd_value: 250.5 }),
      makeTrade({ id: 2, base_asset: "ETH", side: "sell", usd_value: 100 }),
    ];
    mockHookReturn = { trades, error: undefined, isLoading: false };

    render(<TradeHistory profileId={1} />);

    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("ETH")).toBeInTheDocument();
    expect(screen.getByText("$250.50")).toBeInTheDocument();
    expect(screen.getByText("$100.00")).toBeInTheDocument();
  });

  it("shows empty state when trade list is empty", () => {
    mockHookReturn = { trades: [], error: undefined, isLoading: false };

    render(<TradeHistory profileId={1} />);

    expect(screen.getByText(/no trades yet/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows error text and styling for a failed-status row", () => {
    const trades = [
      makeTrade({
        id: 3,
        status: "failed",
        error: "Insufficient balance",
        base_asset: "SOL",
      }),
    ];
    mockHookReturn = { trades, error: undefined, isLoading: false };

    render(<TradeHistory profileId={1} />);

    // The status badge says "failed"
    expect(screen.getByText("failed")).toBeInTheDocument();
    // The error message is displayed inline
    expect(screen.getByText(/insufficient balance/i)).toBeInTheDocument();
    // The row has the failed highlight class (via the tr element)
    const row = screen.getByText("SOL").closest("tr");
    expect(row?.className).toMatch(/red/);
  });

  it("distinguishes buy vs sell with different visual classes", () => {
    const trades = [
      makeTrade({ id: 1, side: "buy" }),
      makeTrade({ id: 2, side: "sell" }),
    ];
    mockHookReturn = { trades, error: undefined, isLoading: false };

    render(<TradeHistory profileId={1} />);

    const buyBadge = screen.getByText("buy");
    const sellBadge = screen.getByText("sell");

    expect(buyBadge.className).toMatch(/green/);
    expect(sellBadge.className).toMatch(/red/);
  });

  it("shows a hint when no profile is selected (aggregate view)", () => {
    render(<TradeHistory profileId={null} />);

    expect(screen.getByText(/select a profile/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows loading skeletons while fetching", () => {
    mockHookReturn = { trades: undefined, error: undefined, isLoading: true };

    render(<TradeHistory profileId={1} />);

    expect(screen.getByRole("status", { name: /loading trade history/i })).toBeInTheDocument();
  });

  it("shows an error alert when the hook returns an error", () => {
    mockHookReturn = {
      trades: undefined,
      error: new Error("Network timeout"),
      isLoading: false,
    };

    render(<TradeHistory profileId={1} />);

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toMatch(/network timeout/i);
  });
});
