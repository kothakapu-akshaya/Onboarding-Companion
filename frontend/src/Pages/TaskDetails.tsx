import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import { useNavigate, useParams } from "react-router-dom";

import Layout from "../components/Layout";
import { onboardingTasks } from "../data/onboardingTasks";
import { useOnboarding } from "../context/onboarding";

import {
  deleteEvidence,
  getEvidenceUrl,
  listEvidence,
  onboardingErrorMessage,
  uploadEvidence,
  upsertOnboardingProgress,
} from "../services/onboarding";
import type { OnboardingEvidence } from "../types/onboarding";

import "../styles/TaskDetails.css";

const MAX_EVIDENCE = 6;
const MAX_EVIDENCE_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif"];
const ALLOWED_MIME = ["image/png", "image/jpeg", "image/gif"];

async function fetchEvidenceForTask(taskKey: string) {
  const items = await listEvidence(taskKey);

  const urls: Record<string, string> = {};

  for (const item of items) {
    try {
      const { evidence_url } = await getEvidenceUrl(taskKey, item.id);
      urls[item.id] = evidence_url;
    } catch {
      // One failing presigned URL must not break the whole grid.
    }
  }

  return { items, urls };
}

function TaskDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { progressMap, applyProgress } = useOnboarding();

  const task = useMemo(
    () => onboardingTasks.find((t) => t.id === Number(id)),
    [id]
  );

  const [evidence, setEvidence] = useState<OnboardingEvidence[]>([]);
  const [evidenceUrls, setEvidenceUrls] = useState<Record<string, string>>({});
  const [evidenceLoading, setEvidenceLoading] = useState(true);
  const [evidenceError, setEvidenceError] = useState("");
  const [actionError, setActionError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [completing, setCompleting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const evidenceVersionRef = useRef(0);

  const taskKey = task ? String(task.id) : "";

  useEffect(() => {
    if (!selectedImage) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedImage(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedImage]);

  useEffect(() => {
    if (!taskKey) return;

    let ignore = false;
    const startVersion = evidenceVersionRef.current;

    void fetchEvidenceForTask(taskKey)
      .then(({ items, urls }) => {
        if (ignore) return;
        if (startVersion !== evidenceVersionRef.current) return;

        setEvidence(items);
        setEvidenceUrls(urls);
        setEvidenceLoading(false);
      })
      .catch((err) => {
        if (ignore) return;
        if (startVersion !== evidenceVersionRef.current) return;

        setEvidenceError(onboardingErrorMessage(err));
        setEvidenceLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [taskKey]);

  function reloadEvidence() {
    setEvidenceLoading(true);
    setEvidenceError("");

    const startVersion = evidenceVersionRef.current;

    void fetchEvidenceForTask(taskKey)
      .then(({ items, urls }) => {
        if (startVersion !== evidenceVersionRef.current) return;

        setEvidence(items);
        setEvidenceUrls(urls);
        setEvidenceLoading(false);
      })
      .catch((err) => {
        if (startVersion !== evidenceVersionRef.current) return;

        setEvidenceError(onboardingErrorMessage(err));
        setEvidenceLoading(false);
      });
  }

  if (!task) {
    return (
      <Layout>
        <h2>Task not found</h2>
      </Layout>
    );
  }

  const progressItem = taskKey ? progressMap[taskKey] : undefined;
  const isCompleted = progressItem?.status === "completed";
  const atLimit = evidence.length >= MAX_EVIDENCE;

  function validateFiles(files: File[]): string | null {
    if (evidence.length + files.length > MAX_EVIDENCE) {
      return `Maximum ${MAX_EVIDENCE} images per task.`;
    }

    for (const file of files) {
      const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

      if (
        !ALLOWED_EXTENSIONS.includes(extension) ||
        !ALLOWED_MIME.includes(file.type)
      ) {
        return `${file.name} is not a supported image. Please use PNG, JPG or GIF.`;
      }

      if (file.size > MAX_EVIDENCE_FILE_SIZE) {
        return `${file.name} is larger than 5 MB. Please use a smaller image.`;
      }
    }

    return null;
  }

  async function handleImageChange(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files ? Array.from(event.target.files) : [];
    setActionError("");

    const validationError = validateFiles(files);
    if (validationError) {
      setActionError(validationError);
      return;
    }

    if (files.length === 0) return;

    setUploading(true);
    setUploadProgress(0);

    try {
      for (const file of files) {
        const created = await uploadEvidence(taskKey, file, (progressEvent) => {
          if (progressEvent.total && progressEvent.total > 0) {
            setUploadProgress(
              Math.round((progressEvent.loaded / progressEvent.total) * 100)
            );
          }
        });

        setEvidence((previous) => [...previous, created]);
        setUploadProgress(100);

        evidenceVersionRef.current += 1;

        void getEvidenceUrl(taskKey, created.id)
          .then(({ evidence_url }) =>
            setEvidenceUrls((previous) => ({
              ...previous,
              [created.id]: evidence_url,
            }))
          )
          .catch(() => {
            // Presigned URL will simply be unavailable for this thumbnail.
          });
      }
    } catch (err) {
      setActionError(onboardingErrorMessage(err));
    } finally {
      setUploading(false);
      setUploadProgress(null);
      setFileInputKey((key) => key + 1);
    }
  }

  async function handleComplete() {
    if (evidence.length === 0) {
      setActionError("Please upload at least one screenshot.");
      return;
    }

    setCompleting(true);
    setActionError("");

    try {
      const updated = await upsertOnboardingProgress(taskKey, {
        status: "completed",
        notes: null,
      });
      applyProgress(updated);
    } catch (err) {
      setActionError(onboardingErrorMessage(err));
    } finally {
      setCompleting(false);
    }
  }

  async function handleDelete(item: OnboardingEvidence) {
    setDeletingId(item.id);
    setActionError("");

    try {
      await deleteEvidence(taskKey, item.id);

      if (isCompleted) {
        const updated = await upsertOnboardingProgress(taskKey, {
          status: "pending",
          notes: null,
        });
        applyProgress(updated);
      }

      evidenceVersionRef.current += 1;

      setEvidence((previous) =>
        previous.filter((entry) => entry.id !== item.id)
      );
      setEvidenceUrls((previous) => {
        const next = { ...previous };
        delete next[item.id];
        return next;
      });
    } catch (err) {
      setActionError(onboardingErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <Layout>
      <h1>{task.title}</h1>

      {task.category && (
        <p className="task-details-category">{task.category}</p>
      )}

      <p>{task.description}</p>

      <a
        className="task-details-link"
        href="https://code.swecha.org/internships/intern-instructions/-/blob/main/workbench-setup.md?ref_type=heads"
        target="_blank"
        rel="noopener noreferrer"
      >
        📖 Open Official Workbench Guide
      </a>

      {!isCompleted && (
        <div className="task-details-upload">
          <h3>Upload Evidence</h3>

          <input
            key={fileInputKey}
            className="task-details-file-input"
            type="file"
            multiple
            accept="image/png,image/jpeg,image/gif"
            disabled={uploading || atLimit}
            onChange={handleImageChange}
          />

          {uploading && (
            <p className="task-details-hint" role="status">
              Uploading… {uploadProgress !== null ? `${uploadProgress}%` : ""}
            </p>
          )}

          <p className="task-details-hint">
            Minimum 1 image • Maximum {MAX_EVIDENCE} images • PNG, JPG or GIF
            up to 5 MB each
          </p>
        </div>
      )}

      {(actionError || evidenceError) && (
        <p className="task-details-error" role="alert">
          {actionError || evidenceError}
        </p>
      )}

      {evidenceLoading && (
        <p className="task-details-hint" role="status">
          Loading evidence…
        </p>
      )}

      {evidenceError && !evidenceLoading && (
        <button
          type="button"
          className="btn-secondary"
          onClick={reloadEvidence}
        >
          Retry loading evidence
        </button>
      )}

      {!evidenceLoading && !evidenceError && evidence.length === 0 && (
        <p className="task-details-hint">No evidence uploaded yet.</p>
      )}

      {evidence.length > 0 && (
        <>
          <h3>Evidence</h3>

          <div className="task-details-evidence-grid">
            {evidence.map((item, index) => {
              const url = evidenceUrls[item.id];

              return (
                <div className="task-details-evidence-card" key={item.id}>
                  <img
                    className="task-details-evidence-img"
                    src={url ?? ""}
                    alt={`Evidence ${index + 1} (${item.file_name})`}
                    tabIndex={url ? 0 : -1}
                    role={url ? "button" : undefined}
                    onClick={() => {
                      if (url) setSelectedImage(url);
                    }}
                    onKeyDown={(event) => {
                      if (!url) return;
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedImage(url);
                      }
                    }}
                  />
                  {!url && (
                    <p className="task-details-hint">
                      Preview unavailable
                    </p>
                  )}
                  <button
                    type="button"
                    className="task-details-evidence-remove"
                    aria-label={`Remove evidence ${index + 1}`}
                    disabled={deletingId === item.id}
                    onClick={() => void handleDelete(item)}
                  >
                    {deletingId === item.id ? "Removing…" : "Remove"}
                  </button>
                </div>
              );
            })}
          </div>
        </>
      )}

      <div className="task-details-actions">
        {!isCompleted ? (
          <button
            type="button"
            disabled={uploading || completing}
            aria-busy={completing}
            onClick={() => void handleComplete()}
          >
            {completing ? "Saving…" : "Mark as Completed"}
          </button>
        ) : (
          <button type="button" disabled>
            ✅ Task Completed
          </button>
        )}

        <br />
        <br />

        <button
          type="button"
          className="btn-secondary"
          onClick={() => navigate("/tasks")}
        >
          ← Back to Checklist
        </button>
      </div>

      {selectedImage && (
        <div
          className="task-details-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Evidence preview"
          onClick={() => setSelectedImage(null)}
        >
          <button
            type="button"
            className="task-details-overlay-close"
            aria-label="Close preview"
            onClick={() => setSelectedImage(null)}
          >
            ×
          </button>
          <img src={selectedImage} alt="Evidence preview" />
        </div>
      )}
    </Layout>
  );
}

export default TaskDetails;