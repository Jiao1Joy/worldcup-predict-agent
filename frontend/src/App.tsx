import { useState } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AppRoutes } from './app/router';
import { forecastFixture } from './test/forecast-fixture';

export function App() {
  const [forecast] = useState(forecastFixture);
  return (
    <BrowserRouter>
      <AppRoutes forecast={forecast} />
    </BrowserRouter>
  );
}
