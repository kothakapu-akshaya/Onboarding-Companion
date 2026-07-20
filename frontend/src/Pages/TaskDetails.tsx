import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import Layout from "../components/Layout";
import { onboardingTasks } from "../data/onboardingTasks";
import { getProgress, saveTask } from "../utils/taskStorage";

function TaskDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const task = useMemo(
    () => onboardingTasks.find((t) => t.id === Number(id)),
    [id]
  );

  if (!task) {
    return (
      <Layout>
        <h2>Task not found</h2>
      </Layout>
    );
  }

  // TypeScript now knows task definitely exists
  const currentTask = task;

  const progress = getProgress();
  const completedTask = progress[currentTask.id];

  const isCompleted = completedTask?.completed ?? false;

  const [previewUrls, setPreviewUrls] = useState<string[]>(
    completedTask?.images || []
  );

  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  async function handleImageChange(
    e: React.ChangeEvent<HTMLInputElement>
  ) {
    if (!e.target.files) return;

    const files = Array.from(e.target.files);

    if (files.length > 5) {
      alert("Maximum 5 images allowed.");
      return;
    }

    const base64Images = await Promise.all(
      files.map(
        (file) =>
          new Promise<string>((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = () => resolve(reader.result as string);
            reader.onerror = reject;

            reader.readAsDataURL(file);
          })
      )
    );

    setPreviewUrls(base64Images);
  }

  function handleComplete() {
    if (previewUrls.length === 0) {
      alert("Please upload at least one screenshot.");
      return;
    }

    saveTask(currentTask.id, previewUrls);

    alert("Task marked as completed.");

    navigate("/tasks");
  }

  return (
    <Layout>
      <h1>{currentTask.title}</h1>

      <br />

      <p>{currentTask.description}</p>

      <br />

      <a
        href="https://code.swecha.org/internships/intern-instructions/-/blob/main/workbench-setup.md?ref_type=heads"
        target="_blank"
        rel="noopener noreferrer"
      >
        📖 Open Official Workbench Guide
      </a>

      <br />
      <br />

      {!isCompleted && (
        <>
          <h3>Upload Evidence</h3>

          <input
            type="file"
            multiple
            accept="image/*"
            onChange={handleImageChange}
          />

          <p>Minimum 1 image • Maximum 5 images</p>

          <br />
        </>
      )}

      {previewUrls.length > 0 && (
        <>
          <h3>Evidence</h3>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "15px",
            }}
          >
            {previewUrls.map((image, index) => (
              <img
                key={index}
                src={image}
                alt={`Evidence ${index + 1}`}
                onClick={() => setSelectedImage(image)}
                style={{
                  width: "180px",
                  height: "120px",
                  objectFit: "cover",
                  cursor: "pointer",
                  borderRadius: "8px",
                  border: "1px solid #ddd",
                }}
              />
            ))}
          </div>

          <br />
        </>
      )}

      {!isCompleted ? (
        <button onClick={handleComplete}>
          Mark as Completed
        </button>
      ) : (
        <button disabled>
          ✅ Task Completed
        </button>
      )}

      <br />
      <br />

      <button onClick={() => navigate("/tasks")}>
        ← Back to Checklist
      </button>

      {selectedImage && (
        <div
          onClick={() => setSelectedImage(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.8)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 9999,
            cursor: "pointer",
          }}
        >
          <img
            src={selectedImage}
            alt="Preview"
            style={{
              maxWidth: "90%",
              maxHeight: "90%",
              borderRadius: "10px",
            }}
          />
        </div>
      )}
    </Layout>
  );
}

export default TaskDetails;