import type { RunEvent } from '../domain/run';

export function EventTimeline({ events }: { events: RunEvent[] }) {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  return (
    <section aria-label="Event timeline">
      <h2>Event Timeline</h2>
      <ol className="event-timeline">
        {ordered.map((event) => (
          <li key={event.sequence}>
            <time>{event.sequence}</time>
            <span>{event.event_type.toUpperCase()}</span>
            <strong>{event.step_id ?? 'run'}</strong>
            <code>{JSON.stringify(event.payload)}</code>
          </li>
        ))}
      </ol>
    </section>
  );
}
