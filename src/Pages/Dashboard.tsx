import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import ProgressCard from "../components/ProgressCard";
import TaskCard from "../components/TaskCard";
import EventCard from "../components/EventCard";

import { getProfile } from "../services/user";
import { getEvents } from "../services/event";

function Dashboard() {
  const [user, setUser] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);

  // Dummy task data (until backend provides task APIs)
  const totalTasks = 12;
  const completedTasks = 8;

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const profile = await getProfile();
        setUser(profile);

        const eventData = await getEvents();
        setEvents(eventData);
      } catch (error) {
        console.error("Failed to load dashboard", error);
      }
    };

    loadDashboard();
  }, []);

  return (
    <Layout>
      <h1>
        Welcome, {user ? user.name : "User"} 👋
      </h1>

      <br />

      <ProgressCard
        totalTasks={totalTasks}
        completedTasks={completedTasks}
        upcomingEvents={events.length}
      />

      <br />

      <h2>Today's Tasks</h2>

      <TaskCard
        title="Setup Laptop"
        status="Completed"
        buttonText="View"
      />

      <TaskCard
        title="Configure Email"
        status="Pending"
        buttonText="Mark Complete"
      />

      <br />

      <h2>Upcoming Events</h2>

      {events.length === 0 ? (
        <p>No upcoming events.</p>
      ) : (
        events.slice(0, 2).map((event) => (
          <EventCard
            key={event.uid}
            title={event.name}
            date={new Date(event.start_date).toLocaleDateString()}
            location={event.description || "Not specified"}
            buttonText="View"
          />
        ))
      )}
    </Layout>
  );
}

export default Dashboard;