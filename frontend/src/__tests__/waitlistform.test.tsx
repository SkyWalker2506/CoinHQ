import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import WaitlistForm from "@/components/WaitlistForm";

describe("WaitlistForm", () => {
  beforeEach(() => {
    localStorage.clear();
    // @ts-expect-error — plausible is attached at runtime in production
    window.plausible = vi.fn();
    vi.restoreAllMocks();
  });

  it("renders email input and submit button", () => {
    render(<WaitlistForm />);
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /notify me/i }),
    ).toBeInTheDocument();
  });

  it("rejects an invalid email and shows alert message without POSTing", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const user = userEvent.setup();
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("you@example.com");
    await user.type(input, "not-an-email");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/valid email/i);
    expect(localStorage.getItem("coinhq_waitlist_emails")).toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("successful POST (201) → success state, analytics fired, localStorage mirrored", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "created" }), { status: 201 }),
    );
    const user = userEvent.setup();
    render(<WaitlistForm />);
    await user.type(screen.getByPlaceholderText("you@example.com"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    expect(screen.getByRole("status")).toHaveTextContent(/on the list/i);
    // localStorage mirrored after backend success
    const stored = JSON.parse(localStorage.getItem("coinhq_waitlist_emails") || "[]");
    expect(stored).toContain("user@example.com");
    // @ts-expect-error — plausible mock
    expect(window.plausible).toHaveBeenCalled();
  });

  it("duplicate POST (200) → success state with already-joined message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "already exists" }), { status: 200 }),
    );
    const user = userEvent.setup();
    render(<WaitlistForm />);
    await user.type(screen.getByPlaceholderText("you@example.com"), "dup@example.com");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    expect(screen.getByRole("status")).toHaveTextContent(/already on the list/i);
  });

  it("POST network error → falls back to localStorage, still shows success UX", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"));
    const user = userEvent.setup();
    render(<WaitlistForm />);
    await user.type(screen.getByPlaceholderText("you@example.com"), "fallback@example.com");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    // Success UX must still render
    expect(screen.getByRole("status")).toHaveTextContent(/on the list/i);
    // Email saved to localStorage as fallback
    const stored = JSON.parse(localStorage.getItem("coinhq_waitlist_emails") || "[]");
    expect(stored).toContain("fallback@example.com");
    // Analytics still fires
    // @ts-expect-error — plausible mock
    expect(window.plausible).toHaveBeenCalled();
  });

  it("POST 500 → falls back to localStorage, still shows success UX", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("Server error", { status: 500 }),
    );
    const user = userEvent.setup();
    render(<WaitlistForm />);
    await user.type(screen.getByPlaceholderText("you@example.com"), "err@example.com");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    expect(screen.getByRole("status")).toHaveTextContent(/on the list/i);
    const stored = JSON.parse(localStorage.getItem("coinhq_waitlist_emails") || "[]");
    expect(stored).toContain("err@example.com");
  });

  it("treats a localStorage-duplicate re-submission as duplicate and does not double-store", async () => {
    localStorage.setItem(
      "coinhq_waitlist_emails",
      JSON.stringify(["dup@example.com"]),
    );
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("offline"));
    const user = userEvent.setup();
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("you@example.com");
    await user.type(input, "dup@example.com");
    await user.click(
      screen.getByRole("button", { name: /update email|notify me/i }),
    );

    const stored = JSON.parse(
      localStorage.getItem("coinhq_waitlist_emails") || "[]",
    );
    expect(stored).toEqual(["dup@example.com"]); // unchanged
    expect(screen.getByRole("status")).toHaveTextContent(/already on the list/i);
  });

  it("normalizes email to lowercase before storing", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("offline"));
    const user = userEvent.setup();
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("you@example.com");
    await user.type(input, "MixedCase@Example.COM");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    const stored = JSON.parse(
      localStorage.getItem("coinhq_waitlist_emails") || "[]",
    );
    expect(stored).toEqual(["mixedcase@example.com"]);
  });
});
