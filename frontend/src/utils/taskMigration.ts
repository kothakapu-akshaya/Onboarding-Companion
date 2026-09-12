import {
  getProgress,
  removeTask,
  STORAGE_KEY,
} from "./taskStorage";

import type { OnboardingProgressUpdate } from "../types/onboarding";

export const MIGRATION_JOURNAL_KEY = "onboarding-migration-journal";

export interface MigrationResult {
  migrated: boolean;
  message: string;
}

export type UploadEvidence = (
  taskKey: string,
  file: File
) => Promise<unknown>;

export type SetProgress = (
  taskKey: string,
  payload: OnboardingProgressUpdate
) => Promise<unknown>;

let migrationInFlight = false;

function readJournal(): Record<string, number[]> {
  try {
    const raw = localStorage.getItem(MIGRATION_JOURNAL_KEY);
    return raw ? (JSON.parse(raw) as Record<string, number[]>) : {};
  } catch {
    return {};
  }
}

function writeJournal(journal: Record<string, number[]>): void {
  localStorage.setItem(MIGRATION_JOURNAL_KEY, JSON.stringify(journal));
}

export function dataUrlToFile(dataUrl: string, name: string): File {
  const [header, base64 = ""] = dataUrl.split(",");
  const mime = /^data:([^;]+);base64$/.exec(header)?.[1] ?? "image/png";
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);

  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  return new File([bytes], name, { type: mime });
}

export function clearLocalProgress(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    console.error("Could not clear local onboarding progress");
  }
}

/**
 * Migrates legacy browser-local onboarding progress to the onboarding
 * backend. Evidence images are uploaded one at a time (never storing base64
 * in local storage again) and progress is marked completed on the server.
 *
 * Safety rules:
 * - Every successful evidence upload is recorded in a journal BEFORE the
 *   task's local data is cleared, so a reload never duplicates evidence.
 * - Local data for a task is cleared only after ALL of that task's evidence
 *   uploads AND the progress update succeed.
 * - If anything fails, local data is preserved so a later run can resume.
 *
 * The migration is single-flight: concurrent invocations (e.g. React 18
 * StrictMode double effects) are ignored while one is already running.
 */
export async function migrateLegacyOnboarding(
  upload: UploadEvidence,
  setProgress: SetProgress
): Promise<MigrationResult> {
  if (migrationInFlight) {
    return { migrated: false, message: "Migration already in progress" };
  }

  migrationInFlight = true;

  try {
    const local = getProgress();
    const taskIds = Object.keys(local);

    if (taskIds.length === 0) {
      return { migrated: false, message: "No legacy local data to migrate" };
    }

    const failures: string[] = [];
    let migratedAny = false;

    for (const rawId of taskIds) {
      const id = Number(rawId);
      const entry = local[id];

      if (!entry) continue;

      const taskKey = rawId;
      const images = entry.images ?? [];

      const journal = readJournal();
      const uploaded = new Set<number>(journal[taskKey] ?? []);

      const pendingIndices = images
        .map((_, index) => index)
        .filter((index) => !uploaded.has(index));

      let taskFailed = false;

      for (const index of pendingIndices) {
        try {
          await upload(
            taskKey,
            dataUrlToFile(images[index], `evidence-${index + 1}.png`)
          );

          uploaded.add(index);
          writeJournal({ ...readJournal(), [taskKey]: [...uploaded] });
        } catch {
          taskFailed = true;
          failures.push(`evidence for task ${taskKey} (image ${index + 1})`);
        }
      }

      if (taskFailed) continue;

      try {
        await setProgress(taskKey, { status: "completed", notes: null });
      } catch {
        failures.push(`progress for task ${taskKey}`);
        continue;
      }

      removeTask(id);
      migratedAny = true;

      const journalNow = readJournal();
      delete journalNow[taskKey];
      writeJournal(journalNow);
    }

    const remainingJournal = readJournal();
    if (Object.keys(remainingJournal).length === 0) {
      try {
        localStorage.removeItem(MIGRATION_JOURNAL_KEY);
      } catch {
        // Non-critical cleanup failure; journal is preserved for retries.
      }
    }

    if (failures.length > 0) {
      return {
        migrated: migratedAny,
        message: `Migration finished with ${failures.length} failed item(s): ${failures.join(", ")}. Local data was preserved where uploads did not fully succeed.`,
      };
    }

    return {
      migrated: migratedAny,
      message: migratedAny
        ? "Legacy local progress migrated to the server successfully."
        : "No legacy local data to migrate.",
    };
  } finally {
    migrationInFlight = false;
  }
}