import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import {
  getOnboardingProgress,
  onboardingErrorMessage,
  uploadEvidence,
  upsertOnboardingProgress,
} from "../services/onboarding";
import { migrateLegacyOnboarding } from "../utils/taskMigration";
import { useAuth } from "./auth";

import {
  OnboardingContext,
  type OnboardingStatus,
} from "./onboarding";
import type { OnboardingProgress } from "../types/onboarding";

function OnboardingProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();

  const [progress, setProgress] = useState<OnboardingProgress[]>([]);
  const [status, setStatus] = useState<OnboardingStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const applyProgress = useCallback((item: OnboardingProgress) => {
    setProgress((previous) => {
      const next = previous.filter(
        (entry) => entry.task_key !== item.task_key
      );
      return [...next, item];
    });
  }, []);

  const refresh = useCallback(async () => {
    setStatus("loading");
    setError(null);

    try {
      const items = await getOnboardingProgress();
      setProgress(items);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setError(onboardingErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      let active = true;

      queueMicrotask(() => {
        if (!active) return;

        setProgress([]);
        setStatus("idle");
        setError(null);
      });

      return () => {
        active = false;
      };
    }

    let active = true;

    const bootstrap = async () => {
      await Promise.resolve();

      if (!active || !isAuthenticated) return;

      setStatus("loading");
      setError(null);

      try {
        const items = await getOnboardingProgress();

        if (!active) return;

        setProgress(items);
        setStatus("success");

        void migrateLegacyOnboarding(uploadEvidence, upsertOnboardingProgress);
      } catch (err) {
        if (!active) return;

        setStatus("error");
        setError(onboardingErrorMessage(err));
      }
    };

    void bootstrap();

    return () => {
      active = false;
    };
  }, [isAuthenticated]);

  const progressMap = useMemo(() => {
    const map: Record<string, OnboardingProgress> = {};

    for (const item of progress) {
      map[item.task_key] = item;
    }

    return map;
  }, [progress]);

  return (
    <OnboardingContext.Provider
      value={{ progress, progressMap, status, error, refresh, applyProgress }}
    >
      {children}
    </OnboardingContext.Provider>
  );
}

export default OnboardingProvider;