import "../styles/EventCard.css";

type EventCardProps = {
  title: string;
  date: string;
  location: string;
  buttonText: string;
};

function EventCard({
  title,
  date,
  location,
  buttonText,
}: EventCardProps) {
  return (
    <div className="event-card">
      <h3>{title}</h3>

      <p>
        <strong>Date:</strong> {date}
      </p>

      <p>
        <strong>Location:</strong> {location}
      </p>

      <button>{buttonText}</button>
    </div>
  );
}

export default EventCard;