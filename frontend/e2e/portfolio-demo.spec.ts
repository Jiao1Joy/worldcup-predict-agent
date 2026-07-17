import { expect, test } from '@playwright/test';

test('portfolio visitor can inspect and replay an agent run', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: /view agent run/i }).click();
  await expect(page.getByLabel('Agent run graph')).toBeVisible();
  await page.getByTestId('graph-node-simulate').click();
  await expect(page.getByLabel('Step inspector')).toContainText('probability_delta');
  await page.getByRole('tab', { name: /evidence/i }).click();
  await expect(page.getByLabel('Step inspector')).toContainText(/SIM-/);
  await page.getByRole('button', { name: /replay/i }).click();
  await expect(page.getByLabel('Replay event sequence')).toHaveValue('0');
});

test('mobile workbench keeps every inspection surface reachable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('link', { name: /view agent run/i }).click();
  await expect(page.getByLabel('Agent run graph')).toBeVisible();
  await expect(page.getByLabel('Step inspector')).toBeVisible();
  await expect(page.getByLabel('Event timeline')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
