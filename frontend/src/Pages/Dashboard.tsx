import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import ProgressCard from "../components/ProgressCard";
import TaskCard from "../components/TaskCard";
import EventCard from "../components/EventCard";

import { getProfile } from "../services/user";
import { getEvents } from "../services/event";
import { getTasks } from "../services/task";
import type { Task } from "../services/task";

type UserProfile = {
  name: string;
  email: string;
  phone: string;
};

type Event = {
  uid: string;
  name: string;
  description: string;
  start_date: string;
  end_date: string;
};

function Dashboard() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const loadDashboard = async () => {
      // Load Profile
      try {
        const profile = await getProfile();
        setUser(profile);
      } catch (error) {
        console.error("Failed to load profile", error);
      }

      // Load Tasks
      try {
        const taskData = await getTasks();
        setTasks(taskData);
      } catch (error) {
        console.error("Failed to load tasks", error);
      }

      // Load Events
      try {
        const eventData = await getEvents();
        setEvents(eventData);
      } catch (error) {
        console.error("Failed to load events", error);
      }
    };

    loadDashboard();
  }, []);

  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(
    (task) => task.status.toLowerCase() === "completed"
  ).length;

  return (
    <Layout>
      <h1>Welcome, {user ? user.name : "User"} 👋</h1>

      <br />

      <ProgressCard
        totalTasks={totalTasks}
        completedTasks={completedTasks}
        upcomingEvents={events.length}
      />

      <br />

      <h2>Today's Tasks</h2>

      {tasks.length === 0 ? (
        <p>No tasks available.</p>
      ) : (
        tasks.slice(0, 2).map((task) => (
          <TaskCard
            key={task.id}
            title={task.title}
            status={task.status}
            buttonText="View"
          />
        ))
      )}

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