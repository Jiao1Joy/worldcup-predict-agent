import { render, screen } from '@testing-library/react';
import { renderHook, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { useRunController } from '../src/state/use-run-controller';
import { Workbench } from '../src/components/Workbench';
import { completedRunFixture } from '../src/test/completed-run';

test('loads a snapshot and injects a recoverable failure', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(completedRunFixture.state)))
    .mockResolvedValueOnce(new Response(JSON.stringify(completedRunFixture.initial_state)))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...completedRunFixture.state, status: 'recovering' })));
  vi.stubGlobal('fetch', fetchMock);

  const { result } = renderHook(() => useRunController(completedRunFixture.state.run_id, false));
  await waitFor(() => expect(result.current.run).not.toBeNull());
  await waitFor(() => expect(result.current.initialRun?.event_sequence).toBe(0));
  await result.current.injectFailure();

  expect(fetchMock).toHaveBeenLastCalledWith(
    expect.stringContaining('/inject-failure'),
    expect.objectContaining({ method: 'POST' }),
  );
});

test('failure command changes the run to recovery state', async () => {
  const user = userEvent.setup();
  const onInjectFailure = vi.fn().mockResolvedValue(undefined);
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={completedRunFixture.state}
      initialEvents={completedRunFixture.events}
      onInjectFailure={onInjectFailure}
    />,
  );
  await user.click(screen.getByRole('button', { name: /inject tool failure/i }));
  expect(onInjectFailure).toHaveBeenCalledOnce();
});
