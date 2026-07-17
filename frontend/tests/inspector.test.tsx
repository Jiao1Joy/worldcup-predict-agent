import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StepInspector } from '../src/components/StepInspector';
import { completedRunFixture } from '../src/test/completed-run';

test('switches between decision, io, and evidence tabs', async () => {
  const user = userEvent.setup();
  render(<StepInspector run={completedRunFixture.state} stepId="simulate" />);

  expect(screen.getAllByText(/probability_delta/i).length).toBeGreaterThan(0);
  await user.click(screen.getByRole('tab', { name: /evidence/i }));
  expect(screen.getByText(/SIM-/i)).toBeInTheDocument();
});
