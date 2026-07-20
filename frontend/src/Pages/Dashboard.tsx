import { useEffect, useState } from "react";

import Layout from "../components/Layout";
import ProgressCard from "../components/ProgressCard";

import { getProfile } from "../services/user";
import { onboardingTasks } from "../data/onboardingTasks";

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

  // Temporary values
  const totalTasks = onboardingTasks.length;
  const completedTasks = 0;

  return (
    <Layout>
      <h1>Welcome, {user?.name ?? "User"} 👋</h1>

      <br />

      <ProgressCard
        totalTasks={totalTasks}
        completedTasks={completedTasks}
        upcomingEvents={0}
      />

      <br />

      <h2>Onboarding Progress</h2>

      <p>
        Complete all onboarding checklist items to finish your internship setup.
      </p>

      <br />

      <p>
        Total Checklist Items: <strong>{totalTasks}</strong>
      </p>

      <p>
        Completed: <strong>{completedTasks}</strong>
      </p>

      <p>
        Remaining: <strong>{totalTasks - completedTasks}</strong>
      </p>
    </Layout>
  );
}

export default Dashboard;