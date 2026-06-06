import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TradePanel from "@/components/TradePanel";
import type { TradeOrder } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/dashboard",
}));

const order: TradeOrder = {
  id: 1,
  exchange: "binance",
  symbol: "BTCUSDT",
  base_asset: "BTC",
  side: "buy",
  usd_value: 100,
  amount: 0.001,
  status: "filled",
  actor: "owner",
  exchange_order_id: "1",
  error: null,
  created_at: new Date().toISOString(),
};

describe("TradePanel", () => {
  it("shows a no-key message when there are no tradable exchanges", () => {
    render(<TradePanel exchanges={[]} onSubmit={vi.fn()} />);
    expect(screen.getByText(/no trade key/i)).toBeInTheDocument();
  });

  it("renders only the sell action for a sell-only link", () => {
    render(<TradePanel exchanges={["binance"]} direction="sell" onSubmit={vi.fn()} />);
    expect(screen.getByText(/sell only/i)).toBeInTheDocument();
  });

  it("shows the configured limits", () => {
    render(
      <TradePanel
        exchanges={["binance"]}
        allowedCoins="BTC,ETH"
        maxPerOrderUsd={500}
        dailyLimitUsd={2000}
        spentTodayUsd={300}
        onSubmit={vi.fn()}
      />
    );
    expect(screen.getByText(/Allowed coins: BTC,ETH/)).toBeInTheDocument();
    expect(screen.getByText(/Max per order: \$500/)).toBeInTheDocument();
    expect(screen.getByText(/used \$300/)).toBeInTheDocument();
  });

  it("submits a normalized order and shows the result", async () => {
    const onSubmit = vi.fn().mockResolvedValue(order);
    render(<TradePanel exchanges={["binance"]} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText(/asset/i), { target: { value: "btc" } });
    fireEvent.change(screen.getByLabelText(/usd amount/i), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("button", { name: /place buy order/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({
      exchange: "binance",
      asset: "BTC",
      side: "buy",
      usd_amount: 100,
    }));
    expect(await screen.findByText(/Order filled/i)).toBeInTheDocument();
  });
});

describe("trade API helpers", () => {
  const originalFetch = globalThis.fetch;
  beforeEach(() => localStorage.clear());
  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.resetModules();
  });

  it("addKey includes the key_type in the request body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({}),
    });
    const { addKey } = await import("@/lib/api");
    await addKey(1, "binance", "key12345", "secret12345", "trade");

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(JSON.parse(call[1].body).key_type).toBe("trade");
  });

  it("delegateTrade posts to the public share trade endpoint", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve(order),
    });
    const { delegateTrade } = await import("@/lib/api");
    await delegateTrade("tok123", { exchange: "binance", asset: "BTC", side: "buy", usd_amount: 50 });

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toContain("/api/v1/public/share/tok123/trade");
    expect(call[1].method).toBe("POST");
  });
});
