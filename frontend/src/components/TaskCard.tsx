import "../styles/TaskCard.css";
import { useNavigate } from "react-router-dom";

type TaskCardProps = {
  id: number;
  title: string;
  status: string;
};

function TaskCard({ id, title, status }: TaskCardProps) {
  const navigate = useNavigate();

  return (
    <div className="task-card">
      <h3>{title}</h3>

      <p>
        Status: <strong>{status}</strong>
      </p>

      <button onClick={() => navigate(`/tasks/${id}`)}>
        {status === "Completed" ? "View" : "Open"}
      </button>
    </div>
  );
}

export default TaskCard;