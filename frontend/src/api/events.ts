import type { RunEvent } from '../domain/run';

export function subscribeToRunEvents(
  runId: string,
  onEvent: (event: RunEvent) => void,
  eventSourceFactory: (url: string) => EventSource = (url) => new EventSource(url),
): () => void {
  const source = eventSourceFactory(`/api/runs/${runId}/events`);
  const handler = (message: MessageEvent<string>) => onEvent(JSON.parse(message.data) as RunEvent);
  ['plan', 'tool', 'state', 'decision', 'guardrail', 'checkpoint', 'retry', 'human', 'complete']
    .forEach((name) => source.addEventListener(name, handler as EventListener));
  return () => source.close();
}
