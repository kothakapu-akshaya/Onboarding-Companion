import "../styles/ProgressCard.css";

type ProgressCardProps = {
  totalTasks: number;
  completedTasks: number;
};

function ProgressCard({
  totalTasks,
  completedTasks,
}: ProgressCardProps) {
  const pendingTasks = totalTasks - completedTasks;

  const progress =
    totalTasks === 0
      ? 0
      : (completedTasks / totalTasks) * 100;

  return (
    <div className="progress-card">
      <h2>Onboarding Progress</h2>

      <progress
        value={completedTasks}
        max={totalTasks}
      ></progress>

      <p>{progress.toFixed(0)}% Completed</p>

      <div className="progress-info">
        <div>
          <span>Total Tasks</span>
          <strong>{totalTasks}</strong>
        </div>

        <div>
          <span>Completed</span>
          <strong>{completedTasks}</strong>
        </div>

        <div>
          <span>Pending</span>
          <strong>{pendingTasks}</strong>
        </div>
      </div>
    </div>
  );
}

export default ProgressCard;