import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import "@testing-library/jest-dom";

import Login from "../Pages/Login";
import * as auth from "../context/auth";

const loginMock = vi.fn();

vi.mock("../context/auth", async (importOriginal) => {
  const actual = await importOriginal<typeof auth>();
  return {
    ...actual,
    useAuth: () => ({
      user: null,
      status: "unauthenticated",
      isAuthenticated: false,
      login: loginMock,
      logout: vi.fn(),
    }),
  };
});

function renderLogin() {
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

describe("Login Component", () => {
  it("renders the login form", () => {
    renderLogin();

    expect(screen.getByLabelText("Phone Number")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });

  it("does not submit and shows an error when fields are empty", async () => {
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    expect(
      await screen.findByText("Please enter your phone number and password")
    ).toBeInTheDocument();
    expect(loginMock).not.toHaveBeenCalled();
  });

  it("submits credentials and shows a generic error on failure", async () => {
    loginMock.mockRejectedValueOnce(new Error("bad credentials"));

    renderLogin();

    fireEvent.change(screen.getByLabelText("Phone Number"), {
      target: { value: "9999999999" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    expect(
      await screen.findByText("Invalid phone number or password")
    ).toBeInTheDocument();

    await waitFor(() =>
      expect(loginMock).toHaveBeenCalledWith("9999999999", "wrong")
    );
  });
});
