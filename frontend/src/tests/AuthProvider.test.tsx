import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";

import AuthProvider from "../context/AuthProvider";
import { useAuth } from "../context/auth";

const getCurrentUserMock = vi.hoisted(() => vi.fn());

vi.mock("../services/auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/auth")>();
  return { ...actual, getCurrentUser: getCurrentUserMock };
});

const PROGRESS_KEY = "onboarding-progress";

function LogoutButton() {
  const { logout } = useAuth();
  return (
    <button type="button" onClick={logout}>
      Logout
    </button>
  );
}

function renderHarness() {
  return render(
    <AuthProvider>
      <LogoutButton />
    </AuthProvider>
  );
}

describe("AuthProvider logout", () => {
  beforeEach(() => {
    localStorage.clear();
    getCurrentUserMock.mockReset();
    getCurrentUserMock.mockResolvedValue({
      id: "9",
      username: "intern",
      name: "Ravi",
      role: "intern",
    });
  });

  it("clears only authentication state and preserves local onboarding data", async () => {
    localStorage.setItem("token", "jwt-token");
    localStorage.setItem(
      PROGRESS_KEY,
      JSON.stringify({ 1: { completed: true, images: [] } })
    );

    renderHarness();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Logout" })).toBeInTheDocument()
    );

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    expect(localStorage.getItem("token")).toBeNull();
    expect(localStorage.getItem(PROGRESS_KEY)).not.toBeNull();
  });
});