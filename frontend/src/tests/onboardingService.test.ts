import { AxiosError, type AxiosProgressEvent } from "axios";
import { describe, it, expect, vi, beforeEach } from "vitest";

import onboardingApi from "../api/onboardingAxios";
import {
  deleteEvidence,
  getEvidenceUrl,
  getOnboardingProgress,
  listEvidence,
  onboardingErrorMessage,
  uploadEvidence,
  upsertOnboardingProgress,
} from "../services/onboarding";

import type { OnboardingEvidence, OnboardingProgress } from "../types/onboarding";

const progressItem: OnboardingProgress = {
  id: 1,
  user_id: 9,
  task_key: "1",
  status: "completed",
  notes: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const evidenceItem: OnboardingEvidence = {
  id: 40,
  user_id: 9,
  task_key: "1",
  object_key: "evidence/9/1/40",
  file_name: "shot.png",
  mime_type: "image/png",
  file_size: 1024,
  created_at: "2026-01-01T00:00:00Z",
};

function apiError(status: number | undefined, detail?: unknown): AxiosError {
  return new AxiosError(
    status ? "Request failed" : "Network Error",
    status ? "ERR_BAD_REQUEST" : "ERR_NETWORK",
    undefined,
    undefined,
    status
      ? ({ status, data: detail === undefined ? {} : { detail } } as never)
      : undefined
  );
}

describe("onboarding service", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the full progress list", async () => {
    const spy = vi
      .spyOn(onboardingApi, "get")
      .mockResolvedValue({ data: [progressItem] } as never);

    const result = await getOnboardingProgress();

    expect(spy).toHaveBeenCalledWith("/onboarding/progress");
    expect(result).toEqual([progressItem]);
  });

  it("upserts progress for a task key", async () => {
    const spy = vi
      .spyOn(onboardingApi, "put")
      .mockResolvedValue({ data: progressItem } as never);

    const result = await upsertOnboardingProgress("1", {
      status: "completed",
      notes: null,
    });

    expect(spy).toHaveBeenCalledWith("/onboarding/progress/1", {
      status: "completed",
      notes: null,
    });
    expect(result).toEqual(progressItem);
  });

  it("uploads evidence as multipart form data with progress reporting", async () => {
    const file = new File(["x"], "shot.png", { type: "image/png" });

    const spy = vi.spyOn(onboardingApi, "post").mockImplementation(
      (_url, _data, config) => {
        config?.onUploadProgress?.({
          loaded: 50,
          total: 100,
        } as AxiosProgressEvent);
        return Promise.resolve({ data: evidenceItem } as never);
      }
    );

    const onUploadProgress = vi.fn();
    const result = await uploadEvidence("1", file, onUploadProgress as never);

    expect(spy).toHaveBeenCalledTimes(1);
    const [url, form] = spy.mock.calls[0] as unknown as [string, FormData];
    expect(url).toBe("/onboarding/tasks/1/evidence");
    expect(form).toBeInstanceOf(FormData);
    expect(form.get("file")).toBe(file);
    expect(onUploadProgress).toHaveBeenCalledWith({ loaded: 50, total: 100 });
    expect(result).toEqual(evidenceItem);
  });

  it("lists, previews and deletes evidence", async () => {
    const getSpy = vi
      .spyOn(onboardingApi, "get")
      .mockResolvedValue({ data: [evidenceItem] } as never);

    expect(await listEvidence("1")).toEqual([evidenceItem]);
    expect(getSpy).toHaveBeenCalledWith("/onboarding/tasks/1/evidence");

    vi.spyOn(onboardingApi, "get").mockResolvedValue({
      data: { evidence_url: "https://presigned/x", expires_minutes: 15 },
    } as never);
    expect(await getEvidenceUrl("1", 40)).toEqual({
      evidence_url: "https://presigned/x",
      expires_minutes: 15,
    });

    const deleteSpy = vi
      .spyOn(onboardingApi, "delete")
      .mockResolvedValue({ status: 204 } as never);
    await deleteEvidence("1", 40);
    expect(deleteSpy).toHaveBeenCalledWith("/onboarding/tasks/1/evidence/40");
  });

  describe("onboardingErrorMessage HTTP mapping", () => {
    it("maps 401 to a session-expired message", () => {
      expect(onboardingErrorMessage(apiError(401))).toBe(
        "Your session has expired. Please sign in again."
      );
    });

    it("surfaces safe validation details for 400", () => {
      expect(onboardingErrorMessage(apiError(400, "Unsupported image file type"))).toBe(
        "Unsupported image file type"
      );
    });

    it("uses a generic message for 400 without a detail", () => {
      expect(onboardingErrorMessage(apiError(400))).toBe(
        "The request was invalid."
      );
    });

    it("maps 404 to a not-found message", () => {
      expect(onboardingErrorMessage(apiError(404))).toBe(
        "Task or evidence was not found."
      );
    });

    it("maps 413 to a file-too-large message", () => {
      expect(onboardingErrorMessage(apiError(413))).toBe(
        "File is too large. Maximum size is 5 MB."
      );
    });

    it("never leaks server internals for 500", () => {
      expect(onboardingErrorMessage(apiError(500, "S3 bucket crashed"))).toBe(
        "Something went wrong on the server. Please try again later."
      );
    });

    it("maps a network failure to a connection message", () => {
      expect(onboardingErrorMessage(apiError(undefined))).toBe(
        "Network error. Please check your connection."
      );
    });

    it("maps non-HTTP errors to a connection message", () => {
      expect(onboardingErrorMessage(new Error("boom"))).toBe(
        "Network error. Please check your connection."
      );
    });
  });
});