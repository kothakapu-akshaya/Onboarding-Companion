import Layout from "../components/Layout";
import TaskCard from "../components/TaskCard";

import { onboardingTasks } from "../data/onboardingTasks";

function Tasks() {
  return (
    <Layout>
      <h1>Onboarding Checklist</h1>

      <br />

      <p>
        Complete each onboarding task to finish your internship setup.
      </p>

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

      {onboardingTasks.map((task) => (
        <TaskCard
          key={task.id}
          id={task.id}
          title={task.title}
          status="Pending"
        />
      ))}
    </Layout>
  );
}

export default Tasks;