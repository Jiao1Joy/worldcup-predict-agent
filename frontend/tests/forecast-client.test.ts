import { assertTournamentForecast } from '../src/domain/forecast';
import { forecastFixture } from '../src/test/forecast-fixture';

test('accepts a complete 104-match forecast fixture', () => {
  expect(() => assertTournamentForecast(forecastFixture)).not.toThrow();
  expect(forecastFixture.matches).toHaveLength(104);
  expect(Object.values(forecastFixture.team_probabilities)).toHaveLength(48);
});

test('rejects an incomplete bracket', () => {
  expect(() => assertTournamentForecast({ ...forecastFixture, matches: [] })).toThrow(/104/);
});
