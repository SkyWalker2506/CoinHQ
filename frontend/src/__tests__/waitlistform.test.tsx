import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import WaitlistForm from "@/components/WaitlistForm";

describe("WaitlistForm", () => {
  beforeEach(() => {
    localStorage.clear();
    // @ts-expect-error — plausible is attached at runtime in production
    window.plausible = vi.fn();
  });

  it("renders email input and submit button", () => {
    render(<WaitlistForm />);
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /notify me/i }),
    ).toBeInTheDocument();
  });

  it("rejects an invalid email and shows alert message", async () => {
    const user = userEvent.setup();
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("you@example.com");
    await user.type(input, "not-an-email");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/valid email/i);
    expect(localStorage.getItem("coinhq_waitlist_emails")).toBeNull();
  });

  it("persists a valid email to localStorage and shows status message", async () => {
    const user = userEvent.setup();
    render(<WaitlistForm />);
    const input = screen.getByPlaceholderText("you@example.com");
    await user.type(input, "user@example.com");
    await user.click(screen.getByRole("button", { name: /notify me/i }));

    const stored = JSON.parse(
      localStorage.getItem("coinhq_waitlist_emails") || "[]",
    );
    expect(stored).toEqual(["user@example.com"]);
    expect(screen.getByRole("status")).toHaveTextContent(/on the list/i);
  });

  it("treats a re-submission as duplicate and does not double-store", async () => {
    localStorage.setItem(
      "coinhq_waitlist_emails",
      JSON.stringify(["dup@example.com"]),
    );
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
