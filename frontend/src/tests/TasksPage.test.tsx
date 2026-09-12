import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";

import Tasks from "../Pages/Tasks";
import type { OnboardingProgress } from "../types/onboarding";

const mocks = vi.hoisted(() => ({
  progress: [] as OnboardingProgress[],
  status: "success" as "idle" | "loading" | "success" | "error",
  error: null as string | null,
  refresh: vi.fn(),
  applyProgress: vi.fn(),
}));

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

vi.mock("../context/auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../context/auth")>();

  return {
    ...actual,
    useAuth: () => ({
      user: { id: "9", username: "intern", name: "Ravi" },
      isAuthenticated: true,
      status: "authenticated",
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
    }),
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

function renderTasks() {
  render(
    <MemoryRouter>
      <Tasks />
    </MemoryRouter>
  );
}

describe("Tasks page", () => {
  beforeEach(() => {
    mocks.progress = [];
    mocks.status = "success";
    mocks.error = null;
    mocks.refresh.mockReset();
  });

  it("shows a loading state while progress is being fetched", () => {
    mocks.status = "loading";

    renderTasks();

    expect(
      screen.getByText("Loading onboarding progress…")
    ).toBeInTheDocument();
  });

  it("marks server-completed tasks as completed", () => {
    mocks.progress = [completed];

    renderTasks();

    expect(screen.getByText("Completed 1 / 16")).toBeInTheDocument();
    expect(screen.getByText("Install Linux Environment")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("shows the failure message and retries on request", () => {
    mocks.status = "error";
    mocks.error = "Something went wrong on the server. Please try again later.";

    renderTasks();

    expect(
      screen.getByRole("alert")
    ).toHaveTextContent(
      "Something went wrong on the server. Please try again later."
    );

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(mocks.refresh).toHaveBeenCalledTimes(1);
  });

  it("surfaces the session-expired prompt for a 401 failure", () => {
    mocks.status = "error";
    mocks.error = "Your session has expired. Please sign in again.";

    renderTasks();

    expect(
      screen.getByText("Your session has expired. Please sign in again.")
    ).toBeInTheDocument();
  });
});