import Layout from "../components/Layout";
import TaskCard from "../components/TaskCard";

function Tasks() {
  return (
    <Layout>
      <h1>My Tasks</h1>

      <br />

      <TaskCard
        title="Setup Laptop"
        status="Completed"
        buttonText="View"
      />

      <TaskCard
        title="Read Company Policies"
        status="Completed"
        buttonText="View"
      />

      <TaskCard
        title="Configure Email"
        status="Pending"
        buttonText="Mark Complete"
      />

      <TaskCard
        title="Meet Your Manager"
        status="Pending"
        buttonText="Mark Complete"
      />

      <TaskCard
        title="Complete Security Training"
        status="Pending"
        buttonText="Mark Complete"
      />
    </Layout>
  );
}

export default Tasks;