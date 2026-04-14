import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock next/navigation before importing anything
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/dashboard",
}));

describe("API client", () => {
  const originalFetch = globalThis.fetch;
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    // Mock window.location
    Object.defineProperty(window, "location", {
      value: { href: "", origin: "http://localhost:3000" },
      writable: true,
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
    });
    vi.resetModules();
  });

  it("getAuthHeader returns empty when no token", async () => {
    // We can test the internal behavior by observing fetch calls
    localStorage.removeItem("token");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });

    const { getProfiles } = await import("@/lib/api");
    await getProfiles();

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = call[1]?.headers;
    expect(headers.Authorization).toBeUndefined();
  });

  it("getAuthHeader includes Bearer token when present", async () => {
    localStorage.setItem("token", "my-jwt-token");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });

    const { getProfiles } = await import("@/lib/api");
    await getProfiles();

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = call[1]?.headers;
    expect(headers.Authorization).toBe("Bearer my-jwt-token");
  });

  it("request retries on 401 with refresh token", async () => {
    localStorage.setItem("token", "expired-token");
    localStorage.setItem("refresh_token", "valid-refresh");

    let callCount = 0;
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/auth/refresh")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ access_token: "new-token" }),
        });
      }
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: "Expired" }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve([{ id: 1, name: "Test" }]),
      });
    });

    const { getProfiles } = await import("@/lib/api");
    const result = await getProfiles();

    expect(result).toEqual([{ id: 1, name: "Test" }]);
    expect(localStorage.getItem("token")).toBe("new-token");
  });

  it("request throws on non-401 error", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({ detail: "Server error" }),
    });

    const { getProfiles } = await import("@/lib/api");
    await expect(getProfiles()).rejects.toThrow("Server error");
  });

  it("redirects to login when refresh fails", async () => {
    localStorage.setItem("token", "expired-token");
    localStorage.setItem("refresh_token", "bad-refresh");

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/auth/refresh")) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: "Invalid refresh" }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Expired" }),
      });
    });

    const { getProfiles } = await import("@/lib/api");
    await expect(getProfiles()).rejects.toThrow("Session expired");
    expect(localStorage.getItem("token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("getPublicShare calls correct endpoint", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          token: "abc123",
          profile_name: "Test",
          exchanges: [],
          show_total_value: true,
          show_coin_amounts: false,
          show_exchange_names: false,
          show_allocation_pct: true,
          allow_follow: true,
        }),
    });

    const { getPublicShare } = await import("@/lib/api");
    await getPublicShare("abc123");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(url).toContain("/api/v1/public/share/abc123");
  });

  it("createProfile sends correct payload", async () => {
    localStorage.setItem("token", "valid-token");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({ id: 1, name: "My Portfolio", created_at: "2024-01-01" }),
    });

    const { createProfile } = await import("@/lib/api");
    await createProfile("My Portfolio");

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[1]?.method).toBe("POST");
    expect(JSON.parse(call[1]?.body)).toEqual({ name: "My Portfolio" });
  });
});
