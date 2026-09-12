import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";

import Dashboard from "../Pages/Dashboard";
import type { OnboardingProgress } from "../types/onboarding";
import type { UserProfile } from "../types/user";

const mocks = vi.hoisted(() => ({
  user: null as UserProfile | null,
  progress: [] as OnboardingProgress[],
  status: "success" as "idle" | "loading" | "success" | "error",
  error: null as string | null,
  refresh: vi.fn(),
  applyProgress: vi.fn(),
}));

vi.mock("../context/auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../context/auth")>();

  return {
    ...actual,
    useAuth: () => ({
      user: mocks.user,
      isAuthenticated: true,
      status: "authenticated",
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
    }),
  };
});

vi.mock("../context/onboarding", async (importOriginal) => {
  const actual = await importOriginal<
    typeof import("../context/onboarding")
  >();

  return {
    ...actual,
    useOnboarding: () => {
      const progressMap: Record<string, OnboardingProgress> = {};

      for (const item of mocks.progress) {
        progressMap[item.task_key] = item;
      }

      return {
        progress: mocks.progress,
        progressMap,
        status: mocks.status,
        error: mocks.error,
        refresh: mocks.refresh,
        applyProgress: mocks.applyProgress,
      };
    },
  };
});

const completed: OnboardingProgress = {
  id: 1,
  user_id: 9,
  task_key: "1",
  status: "completed",
  notes: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderDashboard() {
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  );
}

describe("Dashboard page", () => {
  beforeEach(() => {
    mocks.user = {
      id: "9",
      username: "intern",
      name: "Ravi",
      phone: "9000000000",
      email: "ravi@example.com",
    };
    mocks.progress = [];
    mocks.status = "success";
    mocks.error = null;
    mocks.refresh.mockReset();
  });

  it("reflects server progress in the completed count", () => {
    mocks.progress = [completed];

    renderDashboard();

    expect(screen.getByText("Welcome, Ravi 👋")).toBeInTheDocument();
    expect(screen.queryByText("Install Linux Environment")).not.toBeInTheDocument();
  });

  it("shows the loading state during fetch", () => {
    mocks.status = "loading";

    renderDashboard();

    expect(
      screen.getByText("Loading onboarding progress…")
    ).toBeInTheDocument();
  });

  it("shows the error state and retries", () => {
    mocks.status = "error";
    mocks.error = "Network error. Please check your connection.";

    renderDashboard();

    expect(
      screen.getByRole("alert")
    ).toHaveTextContent("Network error. Please check your connection.");

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(mocks.refresh).toHaveBeenCalledTimes(1);
  });
});