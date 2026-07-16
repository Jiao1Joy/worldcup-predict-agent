import { render, screen } from '@testing-library/react';
import { App } from '../src/App';

test('shows the prediction result entry point', () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: /world cup prediction agent/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /view agent run/i })).toBeInTheDocument();
});
