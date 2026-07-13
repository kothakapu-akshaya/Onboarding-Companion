import "../styles/TaskCard.css";

type TaskCardProps = {
  title: string;
  status: "Completed" | "Pending";
  buttonText: string;
};

function TaskCard({
  title,
  status,
  buttonText,
}: TaskCardProps) {
  return (
    <div className="task-card">
      <h3>{title}</h3>

      <p>
        Status: <strong>{status}</strong>
      </p>

      <button>{buttonText}</button>
    </div>
  );
}

export default TaskCard;