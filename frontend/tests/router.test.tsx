import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from '../src/app/router';
import { forecastFixture } from '../src/test/forecast-fixture';

test.each([
  ['/', /all 48 teams/i],
  ['/tournament', /tournament bracket/i],
  ['/explore', /2026 forecast explorer/i],
  ['/backtest', /2022 backtest/i],
])('route %s renders its page', (path, heading) => {
  render(<MemoryRouter initialEntries={[path]}><AppRoutes forecast={forecastFixture} /></MemoryRouter>);
  expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
});
