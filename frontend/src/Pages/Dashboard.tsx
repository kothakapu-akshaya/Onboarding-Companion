import { useEffect, useState } from "react";

import Layout from "../components/Layout";
import ProgressCard from "../components/ProgressCard";
import TaskCard from "../components/TaskCard";

import { getProfile } from "../services/user";

import { onboardingTasks } from "../data/onboardingTasks";
import { getProgress } from "../utils/taskStorage";

type UserProfile = {
  name: string;
  email: string;
  phone: string;
};

function Dashboard() {
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const profile = await getProfile();
        setUser(profile);
      } catch (error) {
        console.error("Failed to load profile", error);
      }
    };

    loadProfile();
  }, []);

  const progress = getProgress();

  const completedTasks = onboardingTasks.filter(
    (task) => progress[task.id]?.completed
  ).length;

  const totalTasks = onboardingTasks.length;

  const pendingTasks = onboardingTasks.filter(
    (task) => !progress[task.id]?.completed
  );

  return (
    <Layout>
      <h1>Welcome, {user ? user.name : "User"} 👋</h1>

      <br />

      <ProgressCard
        totalTasks={totalTasks}
        completedTasks={completedTasks}
      />

      <br />

      <h2>Pending Tasks</h2>

      <br />

      {pendingTasks.length === 0 ? (
        <p>🎉 Congratulations! You have completed all onboarding tasks.</p>
      ) : (
        pendingTasks.slice(0, 3).map((task) => (
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