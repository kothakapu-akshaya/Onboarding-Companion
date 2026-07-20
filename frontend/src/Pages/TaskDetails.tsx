import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import Layout from "../components/Layout";
import { onboardingTasks } from "../data/onboardingTasks";
import { completeTask } from "../utils/taskStorage";

function TaskDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const task = useMemo(
    () => onboardingTasks.find((t) => t.id === Number(id)),
    [id]
  );

  const [images, setImages] = useState<File[]>([]);

  if (!task) {
    return (
      <Layout>
        <h2>Task not found.</h2>
      </Layout>
    );
  }

  const handleImageChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!e.target.files) return;

    const files = Array.from(e.target.files);

    if (files.length > 5) {
      alert("Maximum 5 images allowed.");
      return;
    }

    setImages(files);
  };

  const handleComplete = () => {
    if (images.length === 0) {
      alert("Please upload at least one screenshot.");
      return;
    }

    completeTask(task.id);

    alert("Task completed successfully!");

    navigate("/tasks");
  };

  return (
    <Layout>
      <h1>{task.title}</h1>

      <br />

      <p>{task.description}</p>

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

      <h3>Upload Screenshots</h3>

      <input
        type="file"
        multiple
        accept="image/*"
        onChange={handleImageChange}
      />

      <p>Minimum: 1 image | Maximum: 5 images</p>

      <br />

      {images.length > 0 && (
        <>
          <h3>Selected Images</h3>

          <ul>
            {images.map((image, index) => (
              <li key={index}>{image.name}</li>
            ))}
          </ul>

          <br />
        </>
      )}

      <button onClick={handleComplete}>
        Mark as Completed
      </button>

      <br />
      <br />

      <button onClick={() => navigate("/tasks")}>
        ← Back to Checklist
      </button>
    </Layout>
  );
}

export default TaskDetails;