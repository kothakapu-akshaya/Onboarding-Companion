import Layout from "../components/Layout";
import TaskCard from "../components/TaskCard";

import { onboardingTasks } from "../data/onboardingTasks";
import { useOnboarding } from "../context/onboarding";

function Tasks() {
  const { progressMap, status, error, refresh } = useOnboarding();

  const completedCount = onboardingTasks.filter(
    (task) => progressMap[String(task.id)]?.status === "completed"
  ).length;

  return (
    <Layout>
      <h1>Onboarding Checklist</h1>

      <br />

      <p>Complete each onboarding task to finish your internship setup.</p>

      <br />

      <a
        href="https://code.swecha.org/internships/intern-instructions/-/blob/main/workbench-setup.md?ref_type=heads"
        target="_blank"
        rel="noopener noreferrer"
      >
        📖 Read Official Workbench Setup Guide
      </a>

      <br />
      <br />

      {status === "loading" && (
        <p className="page-status" role="status">
          Loading onboarding progress…
        </p>
      )}

      {status === "error" && (
        <div className="page-error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void refresh()}>
            Retry
          </button>
        </div>
      )}

      <h3>
        Completed {completedCount} / {onboardingTasks.length}
      </h3>

      <br />

      {onboardingTasks.map((task) => (
        <TaskCard
          key={task.id}
          id={task.id}
          title={task.title}
          status={
            progressMap[String(task.id)]?.status === "completed"
              ? "Completed"
              : "Pending"
          }
        />
      ))}
    </Layout>
  );
}

export default Tasks;