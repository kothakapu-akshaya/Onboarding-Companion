import Layout from "../components/Layout";
import ProgressCard from "../components/ProgressCard";
import TaskCard from "../components/TaskCard";

import { useAuth } from "../context/auth";
import { useOnboarding } from "../context/onboarding";

import { onboardingTasks } from "../data/onboardingTasks";

function Dashboard() {
  const { user } = useAuth();
  const { progressMap, status, error, refresh } = useOnboarding();

  const completedTasks = onboardingTasks.filter(
    (task) => progressMap[String(task.id)]?.status === "completed"
  ).length;

  const totalTasks = onboardingTasks.length;

  const pendingTasks = onboardingTasks.filter(
    (task) => progressMap[String(task.id)]?.status !== "completed"
  );

  return (
    <Layout>
      <h1>Welcome, {user ? user.name : "User"} 👋</h1>

      <br />

      <ProgressCard totalTasks={totalTasks} completedTasks={completedTasks} />

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

      <h2>Pending Tasks</h2>

      <br />

      {pendingTasks.length === 0 ? (
        <p>🎉 Congratulations! You have completed all onboarding tasks.</p>
      ) : (
        pendingTasks
          .slice(0, 3)
          .map((task) => (
            <TaskCard
              key={task.id}
              id={task.id}
              title={task.title}
              status="Pending"
            />
          ))
      )}
    </Layout>
  );
}

export default Dashboard;