import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  MIGRATION_JOURNAL_KEY,
  clearLocalProgress,
  dataUrlToFile,
  migrateLegacyOnboarding,
} from "../utils/taskMigration";
import { STORAGE_KEY, getProgress } from "../utils/taskStorage";

const ONE_PX_PNG =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC";

function seedLocal(
  tasks: Record<string, { completed: boolean; images: string[] }>
) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

describe("dataUrlToFile", () => {
  it("converts a base64 data URL into a typed File", () => {
    const file = dataUrlToFile(ONE_PX_PNG, "evidence-1.png");

    expect(file instanceof File).toBe(true);
    expect(file.type).toBe("image/png");
    expect(file.size).toBeGreaterThan(0);
  });
});

describe("migrateLegacyOnboarding", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("uploads all evidence, marks progress completed and clears local data", async () => {
    seedLocal({ "1": { completed: true, images: [ONE_PX_PNG, ONE_PX_PNG] } });

    const upload = vi.fn().mockResolvedValue(undefined);
    const setProgress = vi.fn().mockResolvedValue({ id: 1 });

    const result = await migrateLegacyOnboarding(upload, setProgress);

    expect(upload).toHaveBeenCalledTimes(2);
    expect(upload.mock.calls[0][0]).toBe("1");
    expect(upload.mock.calls[0][1]).toBeInstanceOf(File);
    expect(setProgress).toHaveBeenCalledWith("1", {
      status: "completed",
      notes: null,
    });
    expect(result.migrated).toBe(true);
    expect(getProgress()).toEqual({});
    expect(localStorage.getItem(MIGRATION_JOURNAL_KEY)).toBeNull();
  });

  it("migrates a completed task that has no images (progress only)", async () => {
    seedLocal({ "5": { completed: true, images: [] } });

    const upload = vi.fn().mockResolvedValue(undefined);
    const setProgress = vi.fn().mockResolvedValue({ id: 2 });

    const result = await migrateLegacyOnboarding(upload, setProgress);

    expect(upload).not.toHaveBeenCalled();
    expect(setProgress).toHaveBeenCalledTimes(1);
    expect(result.migrated).toBe(true);
    expect(getProgress()).toEqual({});
  });

  it("preserves local data when an upload fails and does not duplicate on retry", async () => {
    seedLocal({ "1": { completed: true, images: [ONE_PX_PNG, ONE_PX_PNG] } });

    const upload = vi
      .fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error("upload failed"));
    const setProgress = vi.fn().mockResolvedValue({ id: 1 });

    const first = await migrateLegacyOnboarding(upload, setProgress);

    expect(first.migrated).toBe(false);
    expect(setProgress).not.toHaveBeenCalled();
    expect(getProgress()["1"]).toBeDefined();

    upload.mockReset().mockResolvedValue(undefined);

    await migrateLegacyOnboarding(upload, setProgress);

    expect(upload).toHaveBeenCalledTimes(1);
    expect(setProgress).toHaveBeenCalledTimes(1);
    expect(getProgress()).toEqual({});
  });

  it("preserves local data when the progress update fails and re-uses the upload journal on retry", async () => {
    seedLocal({ "1": { completed: true, images: [ONE_PX_PNG] } });

    const upload = vi.fn().mockResolvedValue(undefined);
    const setProgress = vi.fn().mockRejectedValueOnce(new Error("server down"));

    await migrateLegacyOnboarding(upload, setProgress);

    expect(upload).toHaveBeenCalledTimes(1);
    expect(getProgress()["1"]).toBeDefined();

    setProgress.mockResolvedValue({ id: 1 });

    await migrateLegacyOnboarding(upload, setProgress);

    expect(upload).toHaveBeenCalledTimes(1);
    expect(setProgress).toHaveBeenCalledTimes(2);
    expect(getProgress()).toEqual({});
  });

  it("reports no work when there is nothing to migrate", async () => {
    const upload = vi.fn();
    const setProgress = vi.fn();

    const result = await migrateLegacyOnboarding(upload, setProgress);

    expect(result.migrated).toBe(false);
    expect(upload).not.toHaveBeenCalled();
    expect(setProgress).not.toHaveBeenCalled();
  });

  it("clears all local progress explicitly", () => {
    seedLocal({ "1": { completed: true, images: [] } });

    clearLocalProgress();

    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});