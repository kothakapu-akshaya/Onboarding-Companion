export type OnboardingProgressStatus = "pending" | "in_progress" | "completed";

export interface OnboardingProgress {
  id: number;
  user_id: number;
  task_key: string;
  status: OnboardingProgressStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OnboardingEvidence {
  id: number;
  user_id: number;
  task_key: string;
  object_key: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  created_at: string;
}

export interface OnboardingEvidenceUrl {
  evidence_url: string;
  expires_minutes: number;
}

export interface OnboardingProgressUpdate {
  status: OnboardingProgressStatus;
  notes?: string | null;
}