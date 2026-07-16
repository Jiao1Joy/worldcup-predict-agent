import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ForecastOverviewPage } from '../src/pages/ForecastOverviewPage';
import { forecastFixture } from '../src/test/forecast-fixture';

test('shows champion probability, uncertainty, and version provenance', () => {
  render(<MemoryRouter><ForecastOverviewPage forecast={forecastFixture} /></MemoryRouter>);
  expect(screen.getByRole('heading', { name: forecastFixture.champion.team })).toBeInTheDocument();
  expect(screen.getAllByText(`${(forecastFixture.champion.probability * 100).toFixed(1)}%`).length).toBeGreaterThan(0);
  expect(screen.getByText(new RegExp(forecastFixture.versions.data_version))).toBeInTheDocument();
  expect(screen.getByText(forecastFixture.explanation.uncertainty)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /view agent run/i })).toHaveAttribute('href', `/agent/${forecastFixture.run_id}`);
});
