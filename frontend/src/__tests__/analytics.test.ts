import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { trackEvent, events } from "@/lib/analytics";

describe("Analytics", () => {
  let plausibleMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    plausibleMock = vi.fn();
    (window as any).plausible = plausibleMock;
  });

  afterEach(() => {
    delete (window as any).plausible;
  });

  it("trackEvent calls plausible when available", () => {
    trackEvent("Test Event", { key: "value" });
    expect(plausibleMock).toHaveBeenCalledWith("Test Event", {
      props: { key: "value" },
    });
  });

  it("trackEvent does not throw when plausible is missing", () => {
    delete (window as any).plausible;
    expect(() => trackEvent("Test Event")).not.toThrow();
  });

  it("events.exchangeConnected sends correct event", () => {
    events.exchangeConnected("binance");
    expect(plausibleMock).toHaveBeenCalledWith("Exchange Connected", {
      props: { exchange: "binance" },
    });
  });

  it("events.shareLinkCopied sends correct event", () => {
    events.shareLinkCopied();
    expect(plausibleMock).toHaveBeenCalledWith("Share Link Copied", {
      props: undefined,
    });
  });

  it("events.profileCreated sends correct event", () => {
    events.profileCreated();
    expect(plausibleMock).toHaveBeenCalledWith("Profile Created", {
      props: undefined,
    });
  });
});
