import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MatchDetailPage } from '../src/pages/MatchDetailPage';
import { forecastFixture } from '../src/test/forecast-fixture';

test('match detail renders outcomes, xg, scores, and evidence', () => {
  const match = forecastFixture.matches.find((item) => item.prediction)!;
  render(
    <MemoryRouter initialEntries={[`/matches/${match.match_id}`]}>
      <Routes><Route path="/matches/:matchId" element={<MatchDetailPage forecast={forecastFixture} />} /></Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText(/expected goals/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/score probability matrix/i)).toBeInTheDocument();
  expect(screen.getByText(match.prediction!.evidence_ids[0])).toBeInTheDocument();
});
