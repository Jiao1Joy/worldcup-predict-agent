import { useCallback, useEffect, useState } from 'react';
import { runApi } from '../api/client';
import { subscribeToRunEvents } from '../api/events';
import type { RunEvent, RunState } from '../domain/run';
import { materializeEvent } from './run-reducer';

export function useRunController(runId: string, stream = true) {
  const [run, setRun] = useState<RunState | null>(null);
  const [initialRun, setInitialRun] = useState<RunState | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);

  useEffect(() => {
    void runApi.get(runId).then(setRun);
    void runApi.getInitial(runId).then(setInitialRun);
  }, [runId]);

  useEffect(() => {
    if (!stream) return;
    return subscribeToRunEvents(runId, (event) => {
      setEvents((current) => current.some((item) => item.sequence === event.sequence) ? current : [...current, event]);
      setRun((current) => current ? materializeEvent(current, event) : current);
    });
  }, [runId, stream]);

  const injectFailure = useCallback(async () => {
    const updated = await runApi.injectFailure(runId);
    setRun(updated);
  }, [runId]);

  const approve = useCallback(async (choice: string, actor: string) => {
    const updated = await runApi.approve(runId, choice, actor);
    setRun(updated);
  }, [runId]);

  return { run, initialRun, events, injectFailure, approve, setRun };
}
