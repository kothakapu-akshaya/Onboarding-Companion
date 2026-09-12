import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { STORAGE_KEY, getProgress, saveTask } from "../utils/taskStorage";

describe("taskStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns an empty record when nothing is stored", () => {
    expect(getProgress()).toEqual({});
  });

  it("loads and saves completed tasks", () => {
    const result = saveTask(1, ["data:image/png;base64,AAA"]);

    expect(result.saved).toBe(true);
    expect(getProgress()).toEqual({
      1: { completed: true, images: ["data:image/png;base64,AAA"] },
    });
  });

  it("merges new tasks without losing existing progress", () => {
    saveTask(1, ["img-1"]);
    saveTask(2, ["img-2"]);

    expect(getProgress()).toEqual({
      1: { completed: true, images: ["img-1"] },
      2: { completed: true, images: ["img-2"] },
    });
  });

  it("returns an empty record and clears storage on corrupted JSON", () => {
    localStorage.setItem(STORAGE_KEY, "{not-valid-json");

    expect(getProgress()).toEqual({});
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("reports a quota failure without corrupting state", () => {
    const quotaError = new DOMException("quota", "QuotaExceededError");

    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw quotaError;
    });

    expect(saveTask(3, ["data:image/png;base64,BBB"])).toEqual({
      saved: false,
      reason: "storage",
    });
    expect(getProgress()).toEqual({});
  });

  it("rejects evidence that exceeds the storage budget", () => {
    const oversized = "x".repeat(5 * 1024 * 1024);

    expect(saveTask(4, [`data:image/png;base64,${oversized}`])).toEqual({
      saved: false,
      reason: "quota",
    });
  });
});
