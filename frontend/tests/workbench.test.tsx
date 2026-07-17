import { render, screen } from '@testing-library/react';
import { App } from '../src/App';

test('shows the prediction result entry point', () => {
  render(<App />);
  expect(screen.getByRole('link', { name: /view agent run/i })).toBeInTheDocument();
  expect(screen.getByText(/champion probability/i)).toBeInTheDocument();
});
