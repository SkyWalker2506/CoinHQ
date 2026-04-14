import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock next modules
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

import { Navigation } from "@/components/Navigation";

describe("Navigation", () => {
  beforeEach(() => {
    localStorage.clear();
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });

  it("renders brand name", () => {
    render(<Navigation />);
    expect(screen.getByText("CoinHQ")).toBeInTheDocument();
  });

  it("renders dashboard and settings links", () => {
    render(<Navigation />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders sign out button", () => {
    render(<Navigation />);
    expect(screen.getByText("Sign out")).toBeInTheDocument();
  });

  it("clears token and redirects on logout", async () => {
    localStorage.setItem("token", "test-token");
    const user = userEvent.setup();

    render(<Navigation />);
    await user.click(screen.getByText("Sign out"));

    expect(localStorage.getItem("token")).toBeNull();
    expect(window.location.href).toBe("/login");
  });

  it("highlights active page", () => {
    render(<Navigation />);
    const dashboardLink = screen.getByText("Dashboard");
    expect(dashboardLink.className).toContain("bg-gray-800");
    expect(dashboardLink.className).toContain("text-white");
  });
});
