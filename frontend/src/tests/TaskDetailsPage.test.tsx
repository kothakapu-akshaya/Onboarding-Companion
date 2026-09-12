import { AxiosError } from "axios";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";

import TaskDetails from "../Pages/TaskDetails";
import type { OnboardingEvidence, OnboardingProgress } from "../types/onboarding";

const mocks = vi.hoisted(() => ({
  listEvidence: vi.fn(),
  getEvidenceUrl: vi.fn(),
  uploadEvidence: vi.fn(),
  deleteEvidence: vi.fn(),
  upsertOnboardingProgress: vi.fn(),
  applyProgress: vi.fn(),
  progressMap: {} as Record<string, OnboardingProgress>,
}));

vi.mock("../services/onboarding", async (importOriginal) => {
  const actual = await importOriginal<
    typeof import("../services/onboarding")
  >();

  return {
    ...actual,
    listEvidence: mocks.listEvidence,
    getEvidenceUrl: mocks.getEvidenceUrl,
    uploadEvidence: mocks.uploadEvidence,
    deleteEvidence: mocks.deleteEvidence,
    upsertOnboardingProgress: mocks.upsertOnboardingProgress,
  };
});

vi.mock("../context/onboarding", async (importOriginal) => {
  const actual = await importOriginal<
    typeof import("../context/onboarding")
  >();

  return {
    ...actual,
    useOnboarding: () => ({
      progress: Object.values(mocks.progressMap),
      progressMap: mocks.progressMap,
      status: "success",
      error: null,
      refresh: vi.fn(),
      applyProgress: mocks.applyProgress,
    }),
  };
});

function evidence(id: number): OnboardingEvidence {
  return {
    id,
    user_id: 9,
    task_key: "1",
    object_key: `evidence/9/1/${id}`,
    file_name: `shot-${id}.png`,
    mime_type: "image/png",
    file_size: 1024,
    created_at: "2026-01-01T00:00:00Z",
  };
}

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

function apiError(status: number): AxiosError {
  return new AxiosError(
    "Request failed",
    "ERR_BAD_REQUEST",
    undefined,
    undefined,
    { status, data: {} } as never
  );
}

function file(name: string, type: string, size: number) {
  return new File([new ArrayBuffer(size)], name, { type });
}

function renderTaskDetails() {
  const utils = render(
    <MemoryRouter initialEntries={["/tasks/1"]}>
      <Routes>
        <Route path="/tasks/:id" element={<TaskDetails />} />
      </Routes>
    </MemoryRouter>
  );

  return utils;
}

describe("TaskDetails page", () => {
  beforeEach(() => {
    mocks.progressMap = {};
    mocks.applyProgress.mockReset();
    mocks.listEvidence.mockReset();
    mocks.getEvidenceUrl.mockReset();
    mocks.uploadEvidence.mockReset();
    mocks.deleteEvidence.mockReset();
    mocks.upsertOnboardingProgress.mockReset();
  });

  it("loads evidence from the backend and renders presigned previews", async () => {
    mocks.listEvidence.mockResolvedValue([evidence(10)]);
    mocks.getEvidenceUrl.mockResolvedValue({
      evidence_url: "https://signed/10",
      expires_minutes: 15,
    });

    renderTaskDetails();

    const image = await screen.findByAltText("Evidence 1 (shot-10.png)");

    expect(image).toHaveAttribute("src", "https://signed/10");
    expect(screen.getByText("Evidence")).toBeInTheDocument();
  });

  it("shows a session-expired message when evidence loading returns 401", async () => {
    mocks.listEvidence.mockRejectedValue(apiError(401));

    renderTaskDetails();

    expect(
      await screen.findByText("Your session has expired. Please sign in again.")
    ).toBeInTheDocument();
  });

  it("rejects a selection that exceeds the maximum evidence count", async () => {
    mocks.listEvidence.mockResolvedValue([
      evidence(1),
      evidence(2),
      evidence(3),
      evidence(4),
      evidence(5),
    ]);
    mocks.getEvidenceUrl.mockResolvedValue({
      evidence_url: "u",
      expires_minutes: 15,
    });

    const { container } = renderTaskDetails();
    await screen.findByText("Evidence");

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, {
      target: {
        files: [file("a.png", "image/png", 100), file("b.png", "image/png", 100)],
      },
    });

    expect(
      await screen.findByText("Maximum 6 images per task.")
    ).toBeInTheDocument();
    expect(mocks.uploadEvidence).not.toHaveBeenCalled();
  });

  it("rejects unsupported file types and oversized files", async () => {
    mocks.listEvidence.mockResolvedValue([]);

    const { container } = renderTaskDetails();
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, {
      target: { files: [file("notes.txt", "text/plain", 10)] },
    });

    expect(
      await screen.findByText(
        "notes.txt is not a supported image. Please use PNG, JPG or GIF."
      )
    ).toBeInTheDocument();

    fireEvent.change(input, {
      target: {
        files: [file("big.png", "image/png", 5 * 1024 * 1024 + 1)],
      },
    });

    expect(
      await screen.findByText(
        "big.png is larger than 5 MB. Please use a smaller image."
      )
    ).toBeInTheDocument();

    expect(mocks.uploadEvidence).not.toHaveBeenCalled();
  });

  it("uploads a real File and appends the returned evidence", async () => {
    mocks.listEvidence.mockResolvedValue([]);
    mocks.uploadEvidence.mockResolvedValue(evidence(20));
    mocks.getEvidenceUrl.mockResolvedValue({
      evidence_url: "https://signed/20",
      expires_minutes: 15,
    });

    const { container } = renderTaskDetails();
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const uploadFile = file("shot-new.png", "image/png", 100);

    fireEvent.change(input, { target: { files: [uploadFile] } });

    await waitFor(() =>
      expect(mocks.uploadEvidence).toHaveBeenCalledWith("1", uploadFile, expect.anything())
    );

    const image = await screen.findByAltText("Evidence 1 (shot-20.png)");
    expect(image).toHaveAttribute("src", "https://signed/20");
  });

  it("refuses to mark a task completed without any evidence", async () => {
    mocks.listEvidence.mockResolvedValue([]);

    renderTaskDetails();

    fireEvent.click(screen.getByRole("button", { name: "Mark as Completed" }));

    expect(
      await screen.findByText("Please upload at least one screenshot.")
    ).toBeInTheDocument();
    expect(mocks.upsertOnboardingProgress).not.toHaveBeenCalled();
  });

  it("persists completion to the server and updates progress", async () => {
    mocks.listEvidence.mockResolvedValue([evidence(1)]);
    mocks.getEvidenceUrl.mockResolvedValue({
      evidence_url: "u",
      expires_minutes: 15,
    });
    mocks.upsertOnboardingProgress.mockResolvedValue({
      id: 1,
      user_id: 9,
      task_key: "1",
      status: "completed",
      notes: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    renderTaskDetails();
    await screen.findByText("Evidence");

    fireEvent.click(screen.getByRole("button", { name: "Mark as Completed" }));

    await waitFor(() =>
      expect(mocks.upsertOnboardingProgress).toHaveBeenCalledWith("1", {
        status: "completed",
        notes: null,
      })
    );
    expect(mocks.applyProgress).toHaveBeenCalled();
  });

  it("shows the completed state coming from the server", async () => {
    mocks.progressMap = {
      "1": {
        id: 1,
        user_id: 9,
        task_key: "1",
        status: "completed",
        notes: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    };
    mocks.listEvidence.mockResolvedValue([]);

    renderTaskDetails();

    expect(
      await screen.findByRole("button", { name: "✅ Task Completed" })
    ).toBeDisabled();
    expect(screen.queryByText("Upload Evidence")).not.toBeInTheDocument();
  });

  it("deletes evidence when the remove button is pressed", async () => {
    mocks.listEvidence.mockResolvedValue([evidence(10)]);
    mocks.getEvidenceUrl.mockResolvedValue({
      evidence_url: "https://signed/10",
      expires_minutes: 15,
    });
    mocks.deleteEvidence.mockResolvedValue({ status: 204 } as never);

    renderTaskDetails();
    const image = await screen.findByAltText("Evidence 1 (shot-10.png)");

    fireEvent.click(screen.getByRole("button", { name: "Remove evidence 1" }));

    await waitFor(() =>
      expect(mocks.deleteEvidence).toHaveBeenCalledWith("1", 10)
    );
    await waitFor(() => expect(image).not.toBeInTheDocument());
  });

  it("marks a completed task pending after its evidence is deleted", async () => {
    mocks.progressMap = {
      "1": {
        id: 1,
        user_id: 9,
        task_key: "1",
        status: "completed",
        notes: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    };
    mocks.listEvidence.mockResolvedValue([evidence(10)]);
    mocks.getEvidenceUrl.mockResolvedValue({
      evidence_url: "https://signed/10",
      expires_minutes: 15,
    });
    mocks.deleteEvidence.mockResolvedValue({ status: 204 } as never);
    mocks.upsertOnboardingProgress.mockResolvedValue({
      ...mocks.progressMap["1"],
      status: "pending",
    });

    renderTaskDetails();
    await screen.findByAltText("Evidence 1 (shot-10.png)");

    fireEvent.click(screen.getByRole("button", { name: "Remove evidence 1" }));

    await waitFor(() =>
      expect(mocks.upsertOnboardingProgress).toHaveBeenCalledWith("1", {
        status: "pending",
        notes: null,
      })
    );
    expect(mocks.applyProgress).toHaveBeenCalledWith(
      expect.objectContaining({ status: "pending" })
    );
  });
});