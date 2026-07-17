import { useEffect, useState } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AppRoutes } from './app/router';
import { forecastApi } from './api/forecast-client';
import type { TournamentForecast } from './domain/forecast';
import { forecastFixture } from './test/forecast-fixture';

export function App() {
  const offline = import.meta.env.VITE_PORTFOLIO_OFFLINE !== 'false';
  const [forecast, setForecast] = useState<TournamentForecast | null>(
    offline ? forecastFixture : null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (offline) return;
    void forecastApi.current().then(setForecast).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'forecast request failed');
    });
  }, [offline]);

  if (error) return <main><h1>Forecast unavailable</h1><p>{error}</p></main>;
  if (!forecast) return <main><p>Loading current forecast…</p></main>;
  return (
    <BrowserRouter>
      <AppRoutes forecast={forecast} />
    </BrowserRouter>
  );
}
