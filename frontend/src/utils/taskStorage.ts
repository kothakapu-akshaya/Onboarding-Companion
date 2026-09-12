export const STORAGE_KEY = "onboarding-progress";

export const MAX_EVIDENCE_BUDGET = 4 * 1024 * 1024;

export type CompletedTask = {
  completed: boolean;
  images: string[];
};

export function getProgress(): Record<number, CompletedTask> {
  const data = localStorage.getItem(STORAGE_KEY);

  if (!data) return {};

  try {
    return JSON.parse(data) as Record<number, CompletedTask>;
  } catch {
    console.error("Stored progress is corrupted; resetting");
    localStorage.removeItem(STORAGE_KEY);
    return {};
  }
}

function estimateSerializedSize(
  progress: Record<number, CompletedTask>
): number {
  return new Blob([JSON.stringify(progress)]).size;
}

export function saveTask(
  id: number,
  images: string[]
): { saved: boolean; reason?: "quota" | "storage" } {
  const progress = getProgress();

  progress[id] = {
    completed: true,
    images,
  };

  if (estimateSerializedSize(progress) > MAX_EVIDENCE_BUDGET) {
    return { saved: false, reason: "quota" };
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    return { saved: true };
  } catch {
    return { saved: false, reason: "storage" };
  }
}

export function removeTask(id: number): void {
  const progress = getProgress();

  delete progress[id];

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch {
    console.error("Could not clear migrated local progress");
  }
}
