import { useNavigate } from "react-router-dom";

import "../styles/TaskCard.css";

type Props = {
  id: number;
  title: string;
  status: string;
};

function TaskCard({ id, title, status }: Props) {
  const navigate = useNavigate();

  return (
    <div className="task-card">
      <h3>{title}</h3>

      <p>
        Status:{" "}
        <strong
          className={
            status === "Completed"
              ? "task-status-completed"
              : "task-status-pending"
          }
        >
          {status}
        </strong>
      </p>

      <button type="button" onClick={() => navigate(`/tasks/${id}`)}>
        {status === "Completed" ? "View" : "Start"}
      </button>
    </div>
  );
}

export default TaskCard;
