import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ForecastExplorerPage } from '../src/pages/ForecastExplorerPage';
import { forecastFixture } from '../src/test/forecast-fixture';

test('derives every explorer view from the supplied forecast', async () => {
  const user = userEvent.setup();
  const forecast = {
    ...forecastFixture,
    champion: { team: 'Runtime champion', probability: 0.42 },
    simulation_runs: 123,
  };
  render(<MemoryRouter><ForecastExplorerPage forecast={forecast} /></MemoryRouter>);

  expect(screen.getByText('Runtime champion')).toBeInTheDocument();
  expect(screen.getByText(/123 simulations/i)).toBeInTheDocument();

  await user.click(screen.getByRole('tab', { name: /48-team groups/i }));
  await user.click(screen.getByRole('button', { name: /group A/i }));
  expect(screen.getByRole('heading', { name: 'Group A' })).toBeInTheDocument();
  expect(screen.getByText('Mexico')).toBeInTheDocument();

  await user.click(screen.getByRole('tab', { name: /annex c/i }));
  expect(screen.getByText('3C')).toBeInTheDocument();
  expect(screen.getByText('Brazil')).toBeInTheDocument();

  await user.click(screen.getByRole('tab', { name: /knockout path/i }));
  await user.click(screen.getByRole('button', { name: 'Final' }));
  expect(screen.getAllByText('M104').length).toBeGreaterThan(0);
  expect(screen.getAllByText(forecast.matches[103].winner!).length).toBeGreaterThan(0);
});
