import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { PortfolioSnapshot } from "@/lib/types";

// ── SWR hook mock ─────────────────────────────────────────────────────────────

let mockHookReturn: {
  history: PortfolioSnapshot[] | undefined;
  error: Error | undefined;
  isLoading: boolean;
} = { history: undefined, error: undefined, isLoading: false };

// Track which URL was last requested via the hook
let lastRequestedDays: number | undefined;

vi.mock("@/hooks/usePortfolio", () => ({
  usePortfolioHistory: (profileId: number | null, days: number) => {
    lastRequestedDays = days;
    return mockHookReturn;
  },
}));

// ── recharts mock (mirrors how other chart tests handle it) ──────────────────
// recharts uses ResizeObserver + SVG internals that aren't available in jsdom;
// mock the heavy rendering components while preserving data flow.

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    AreaChart: ({ children, data }: { children: React.ReactNode; data: PortfolioSnapshot[] }) => (
      <div data-testid="area-chart" data-length={data?.length ?? 0}>
        {children}
      </div>
    ),
    Area: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    defs: () => null,
    linearGradient: () => null,
    stop: () => null,
  };
});

// Import component after mocks
import PortfolioHistoryChart from "@/components/PortfolioHistoryChart";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makeSnapshot = (days_ago: number): PortfolioSnapshot => {
  const d = new Date("2026-06-06T00:00:00Z");
  d.setDate(d.getDate() - days_ago);
  return {
    created_at: d.toISOString(),
    total_usd: 10000 + days_ago * 100,
  };
};

const MOCK_HISTORY: PortfolioSnapshot[] = [
  makeSnapshot(5),
  makeSnapshot(4),
  makeSnapshot(3),
  makeSnapshot(2),
  makeSnapshot(1),
  makeSnapshot(0),
];

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PortfolioHistoryChart", () => {
  beforeEach(() => {
    mockHookReturn = { history: undefined, error: undefined, isLoading: false };
    lastRequestedDays = undefined;
  });

  it("renders chart when history data is available", () => {
    mockHookReturn = { history: MOCK_HISTORY, error: undefined, isLoading: false };

    render(<PortfolioHistoryChart profileId={1} />);

    expect(screen.getByRole("img", { name: /portfolio value over time/i })).toBeInTheDocument();
    expect(screen.getByTestId("area-chart")).toBeInTheDocument();
  });

  it("shows empty state when history has fewer than 2 data points", () => {
    mockHookReturn = { history: [], error: undefined, isLoading: false };

    render(<PortfolioHistoryChart profileId={1} />);

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText(/not enough history yet/i)).toBeInTheDocument();
  });

  it("shows loading state while fetching", () => {
    mockHookReturn = { history: undefined, error: undefined, isLoading: true };

    render(<PortfolioHistoryChart profileId={1} />);

    expect(screen.getByRole("status", { name: /loading portfolio history/i })).toBeInTheDocument();
  });

  it("shows error alert when the hook returns an error", () => {
    mockHookReturn = {
      history: undefined,
      error: new Error("Network failure"),
      isLoading: false,
    };

    render(<PortfolioHistoryChart profileId={1} />);

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toMatch(/network failure/i);
  });

  it("shows a hint when no profile is selected", () => {
    render(<PortfolioHistoryChart profileId={null} />);

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText(/select a profile/i)).toBeInTheDocument();
  });

  it("range toggle 7D requests days=7", () => {
    mockHookReturn = { history: MOCK_HISTORY, error: undefined, isLoading: false };

    render(<PortfolioHistoryChart profileId={1} />);

    const btn7 = screen.getByRole("button", { name: "7D" });
    fireEvent.click(btn7);

    expect(lastRequestedDays).toBe(7);
  });

  it("range toggle 90D requests days=90", () => {
    mockHookReturn = { history: MOCK_HISTORY, error: undefined, isLoading: false };

    render(<PortfolioHistoryChart profileId={1} />);

    const btn90 = screen.getByRole("button", { name: "90D" });
    fireEvent.click(btn90);

    expect(lastRequestedDays).toBe(90);
  });

  it("default range is 30D", () => {
    mockHookReturn = { history: MOCK_HISTORY, error: undefined, isLoading: false };

    render(<PortfolioHistoryChart profileId={1} />);

    // Default: hook should have been called with days=30
    expect(lastRequestedDays).toBe(30);
    const btn30 = screen.getByRole("button", { name: "30D" });
    expect(btn30).toHaveAttribute("aria-pressed", "true");
  });
});
