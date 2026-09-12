import { createContext, useContext } from "react";

import type { OnboardingProgress } from "../types/onboarding";

export type OnboardingStatus = "idle" | "loading" | "success" | "error";

export interface OnboardingContextValue {
  progress: OnboardingProgress[];
  progressMap: Record<string, OnboardingProgress>;
  status: OnboardingStatus;
  error: string | null;
  refresh: () => void;
  applyProgress: (item: OnboardingProgress) => void;
}

export const OnboardingContext = createContext<OnboardingContextValue | undefined>(
  undefined
);

export function useOnboarding() {
  const context = useContext(OnboardingContext);

  if (!context) {
    throw new Error("useOnboarding must be used within an OnboardingProvider");
  }

  return context;
}