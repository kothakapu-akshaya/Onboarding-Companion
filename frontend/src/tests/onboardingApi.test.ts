import { describe, it, expect, vi, beforeEach } from "vitest";

import { handleUnauthorized } from "../api/onboardingAxios";

function stubLocation(pathname: string) {
  const locationLike = {
    pathname,
    href: "",
    assign: vi.fn(),
  };

  Object.defineProperty(window, "location", {
    value: locationLike,
    writable: true,
  });

  return locationLike;
}

describe("handleUnauthorized", () => {
  beforeEach(() => {
    localStorage.clear();
    stubLocation("/");
  });

  it("removes the stored token", () => {
    localStorage.setItem("token", "jwt-token");

    handleUnauthorized();

    expect(localStorage.getItem("token")).toBeNull();
  });

  it("redirects to '/' when not already on it", () => {
    localStorage.setItem("token", "jwt-token");
    const location = stubLocation("/dashboard");

    handleUnauthorized();

    expect(location.href).toBe("/");
  });

  it("does not redirect when already on '/'", () => {
    const location = stubLocation("/");

    handleUnauthorized();

    expect(location.href).toBe("");
  });
});