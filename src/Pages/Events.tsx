import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import EventCard from "../components/EventCard";
import { getEvents } from "../services/event";

type Event = {
  uid: string;
  name: string;
  description: string;
  start_date: string;
  end_date: string;
};

function Events() {
  const [events, setEvents] = useState<Event[]>([]);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const data = await getEvents();
        setEvents(data);
      } catch (error) {
        console.error("Failed to fetch events", error);
      }
    };

    fetchEvents();
  }, []);

  return (
    <Layout>
      <h1>Company Events</h1>

      <br />

      {events.length === 0 ? (
        <p>No events available.</p>
      ) : (
        events.map((event) => (
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

export default Events;
