import { useEffect, useState } from "react";

import Layout from "../components/Layout";
import TaskCard from "../components/TaskCard";

import { getTasks } from "../services/task";
import type { Task } from "../services/task";

function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const data = await getTasks();
        setTasks(data);
      } catch (error) {
        console.error("Failed to fetch tasks:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  return (
    <Layout>
      <h1>My Tasks</h1>

      <br />

      {loading ? (
        <p>Loading tasks...</p>
      ) : tasks.length === 0 ? (
        <p>No tasks available.</p>
      ) : (
        tasks.map((task) => (
          <TaskCard
            key={task.id}
            title={task.title}
            status={task.status}
            buttonText={
              task.status.toLowerCase() === "completed"
                ? "View"
                : "Mark Complete"
            }
          />
        ))
      )}
    </Layout>
  );
}

export default Tasks;