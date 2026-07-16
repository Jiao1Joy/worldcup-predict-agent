import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { BacktestPage } from '../src/pages/BacktestPage';

afterEach(() => {
  vi.unstubAllGlobals();
});

test('renders backtest metrics from fixture fallback', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
  render(<MemoryRouter><BacktestPage /></MemoryRouter>);
  await waitFor(() => {
    expect(screen.getByRole('heading', { name: /2022 backtest/i })).toBeInTheDocument();
    expect(screen.getAllByText('0.2144').length).toBeGreaterThan(0);
  });
});

test('reflects mocked API values', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({
      rps: 0.1999, log_loss: 0.95, brier: 0.58, accuracy: 0.6,
      calibration_bins: [{ predicted: 0.5, observed: 0.5, count: 10 }],
    })),
  );
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><BacktestPage /></MemoryRouter>);
  await waitFor(() => expect(screen.getAllByText('0.1999').length).toBeGreaterThan(0));
});
