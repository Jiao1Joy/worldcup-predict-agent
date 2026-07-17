import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TournamentBracket } from '../src/features/bracket/TournamentBracket';
import { forecastFixture } from '../src/test/forecast-fixture';

test('renders every knockout match in official stage columns', () => {
  render(<MemoryRouter><TournamentBracket matches={forecastFixture.matches} /></MemoryRouter>);
  expect(screen.getAllByTestId('knockout-match').length).toBeGreaterThanOrEqual(16);
  expect(screen.getByRole('heading', { name: /round of 32/i })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /^final$/i })).toBeInTheDocument();
});
