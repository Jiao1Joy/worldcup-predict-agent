import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../src/App';
import { RunBar } from '../src/components/RunBar';
import { EventTimeline } from '../src/components/EventTimeline';
import { Workbench } from '../src/components/Workbench';
import { completedRunFixture } from '../src/test/completed-run';

test('shows the prediction result entry point', () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: /world cup prediction agent/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /view agent run/i })).toBeInTheDocument();
});

test('run bar exposes operational metrics', () => {
  render(<RunBar run={completedRunFixture.state} events={completedRunFixture.events} onReplay={() => {}} onInjectFailure={() => {}} />);
  expect(screen.getByText(completedRunFixture.state.status.toUpperCase())).toBeInTheDocument();
  expect(screen.getByText(/tool calls/i)).toBeInTheDocument();
});

test('timeline orders events by sequence', () => {
  render(<EventTimeline events={[...completedRunFixture.events].reverse()} />);
  const rows = screen.getAllByRole('listitem');
  expect(rows[0]).toHaveTextContent(String(Math.min(...completedRunFixture.events.map((event) => event.sequence))));
});

test('selecting a graph step updates the inspector', async () => {
  const user = userEvent.setup();
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={completedRunFixture.state}
      initialEvents={completedRunFixture.events}
    />,
  );

  await user.click(screen.getByTestId('graph-node-critique'));
  expect(screen.getByRole('heading', { name: 'critique' })).toBeInTheDocument();
});

test('waiting run shows approval choices', () => {
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={{ ...completedRunFixture.state, status: 'waiting_for_human' }}
      initialEvents={completedRunFixture.events}
    />,
  );
  expect(screen.getByRole('button', { name: /use official snapshot/i })).toBeInTheDocument();
});

test('workbench exposes graph, inspector, replay, and timeline landmarks', () => {
  render(
    <Workbench
      initialState={completedRunFixture.initial_state}
      initialRun={completedRunFixture.state}
      initialEvents={completedRunFixture.events}
    />,
  );

  expect(screen.getByLabelText('Agent run graph')).toBeInTheDocument();
  expect(screen.getByLabelText('Step inspector')).toBeInTheDocument();
  expect(screen.getByLabelText('Replay event sequence')).toBeInTheDocument();
  expect(screen.getByLabelText('Event timeline')).toBeInTheDocument();
});
