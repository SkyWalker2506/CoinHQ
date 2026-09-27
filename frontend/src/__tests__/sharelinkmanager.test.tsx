import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ShareLink } from "@/lib/types";

const getShareLinks = vi.fn();
const updateShareLink = vi.fn();

vi.mock("@/lib/api", () => ({
  getShareLinks: (...args: unknown[]) => getShareLinks(...args),
  updateShareLink: (...args: unknown[]) => updateShareLink(...args),
  revokeShareLink: vi.fn(),
}));

import ShareLinkManager from "@/components/ShareLinkManager";

const link = (overrides: Partial<ShareLink> = {}): ShareLink =>
  ({
    id: 7,
    profile_id: 1,
    token: "tok_abcdefghijklmnop",
    label: "Muhasebeci",
    expires_at: null,
    is_active: true,
    view_count: 3,
    last_viewed_at: null,
    show_total_value: true,
    show_coin_amounts: true,
    show_exchange_names: true,
    show_allocation_pct: true,
    show_avg_buy_price: false,
    allow_follow: true,
    can_trade: false,
    trade_direction: "both",
    trade_allowed_coins: null,
    trade_max_per_order_usd: null,
    trade_daily_limit_usd: null,
    created_at: "2026-09-01T00:00:00Z",
    ...overrides,
  }) as ShareLink;

const PROFILES = [{ id: 1, name: "Main", created_at: "2026-09-01T00:00:00Z" }] as never;

describe("ShareLinkManager — average buy price on an existing link", () => {
  beforeEach(() => {
    getShareLinks.mockReset();
    updateShareLink.mockReset();
  });

  it("switches it on for a link that is already shared", async () => {
    getShareLinks.mockResolvedValue([link()]);
    updateShareLink.mockResolvedValue(link({ show_avg_buy_price: true }));
    const user = userEvent.setup();
    render(<ShareLinkManager profiles={PROFILES} />);

    const toggle = await screen.findByRole("button", { name: /Show average buy price on Muhasebeci/ });
    expect(toggle).toHaveAttribute("aria-pressed", "false");

    await user.click(toggle);

    expect(updateShareLink).toHaveBeenCalledWith(7, { show_avg_buy_price: true });
    expect(
      screen.getByRole("button", { name: /Hide average buy price on Muhasebeci/ })
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("rolls back and says so when the save fails", async () => {
    getShareLinks.mockResolvedValue([link()]);
    updateShareLink.mockRejectedValue(new Error("500"));
    const user = userEvent.setup();
    render(<ShareLinkManager profiles={PROFILES} />);

    await user.click(await screen.findByRole("button", { name: /Show average buy price/ }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Show average buy price/ })).toHaveAttribute(
        "aria-pressed",
        "false"
      )
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/Couldn't update the link/);
  });
});
