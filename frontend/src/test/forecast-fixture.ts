import fixture from './fixtures/forecast.json';
import type { TournamentForecast } from '../domain/forecast';

const forecast = fixture as TournamentForecast;

export const forecastFixture = forecast;
