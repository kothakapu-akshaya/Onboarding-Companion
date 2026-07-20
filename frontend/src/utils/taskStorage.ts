export const STORAGE_KEY = "onboarding-progress";

export type CompletedTask = {
  completed: boolean;
};

export function getProgress(): Record<number, CompletedTask> {
  const data = localStorage.getItem(STORAGE_KEY);

  if (!data) return {};

  return JSON.parse(data);
}

export function completeTask(id: number) {
  const progress = getProgress();

  progress[id] = {
    completed: true,
  };

  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}