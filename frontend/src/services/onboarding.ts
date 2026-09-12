import axios, { type AxiosProgressEvent } from "axios";

import onboardingApi from "../api/onboardingAxios";

import type {
  OnboardingEvidence,
  OnboardingEvidenceUrl,
  OnboardingProgress,
  OnboardingProgressUpdate,
} from "../types/onboarding";

export function onboardingErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = (error.response?.data as { detail?: unknown } | undefined)
      ?.detail;

    switch (status) {
      case 401:
        return "Your session has expired. Please sign in again.";
      case 400:
        return typeof detail === "string" && detail
          ? detail
          : "The request was invalid.";
      case 404:
        return "Task or evidence was not found.";
      case 413:
        return "File is too large. Maximum size is 5 MB.";
      case 500:
        return "Something went wrong on the server. Please try again later.";
      default:
        return status
          ? `Request failed (${status}). Please try again.`
          : "Network error. Please check your connection.";
    }
  }

  return "Network error. Please check your connection.";
}

export async function getOnboardingProgress(): Promise<OnboardingProgress[]> {
  const { data } = await onboardingApi.get<OnboardingProgress[]>(
    "/onboarding/progress"
  );
  return data;
}

export async function upsertOnboardingProgress(
  taskKey: string,
  payload: OnboardingProgressUpdate
): Promise<OnboardingProgress> {
  const { data } = await onboardingApi.put<OnboardingProgress>(
    `/onboarding/progress/${taskKey}`,
    payload
  );
  return data;
}

export async function uploadEvidence(
  taskKey: string,
  file: File,
  onUploadProgress?: (event: AxiosProgressEvent) => void
): Promise<OnboardingEvidence> {
  const form = new FormData();
  form.append("file", file);

  const { data } = await onboardingApi.post<OnboardingEvidence>(
    `/onboarding/tasks/${taskKey}/evidence`,
    form,
    { onUploadProgress }
  );
  return data;
}

export async function listEvidence(
  taskKey: string
): Promise<OnboardingEvidence[]> {
  const { data } = await onboardingApi.get<OnboardingEvidence[]>(
    `/onboarding/tasks/${taskKey}/evidence`
  );
  return data;
}

export async function getEvidenceUrl(
  taskKey: string,
  evidenceId: number,
  expiresMinutes = 15
): Promise<OnboardingEvidenceUrl> {
  const { data } = await onboardingApi.get<OnboardingEvidenceUrl>(
    `/onboarding/tasks/${taskKey}/evidence/${evidenceId}/url`,
    { params: { expires_minutes: expiresMinutes } }
  );
  return data;
}

export async function deleteEvidence(
  taskKey: string,
  evidenceId: number
): Promise<void> {
  await onboardingApi.delete(
    `/onboarding/tasks/${taskKey}/evidence/${evidenceId}`
  );
}