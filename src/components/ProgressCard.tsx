import "../styles/ProgressCard.css";

type ProgressCardProps = {
  totalTasks: number;
  completedTasks: number;
  upcomingEvents: number;
};

function ProgressCard({
  totalTasks,
  completedTasks,
  upcomingEvents,
}: ProgressCardProps) {
  const pendingTasks = totalTasks - completedTasks;

  const progress =
    totalTasks === 0
      ? 0
      : (completedTasks / totalTasks) * 100;

  return (
    <div className="progress-card">
      <h2>Progress</h2>

      <progress value={completedTasks} max={totalTasks}></progress>

      <p>{progress.toFixed(0)}% Completed</p>

      <div className="progress-info">
        <div>
          <span>Assigned Tasks</span>
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

        <div>
          <span>Upcoming Events</span>
          <strong>{upcomingEvents}</strong>
        </div>
      </div>
    </div>
  );
}

export default ProgressCard;