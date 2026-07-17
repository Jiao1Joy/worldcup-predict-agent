import { expect, test } from '@playwright/test';

test('visitor moves from champion result to bracket, match, and agent evidence', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.getByRole('link', { name: /tournament/i }).first().click();
  await expect(page.getByRole('heading', { name: /tournament bracket/i })).toBeVisible();
  await page.getByTestId('knockout-match').first().click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.goto('/');
  await page.getByRole('link', { name: /view agent run/i }).first().click();
  await expect(page.getByLabel('Agent run graph')).toBeVisible();
});

test('mobile product has no page-level horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.goto('/tournament');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.goto('/explore');
  await expect(page.getByRole('heading', { name: /2026 forecast explorer/i })).toBeVisible();
  await page.getByRole('tab', { name: /annex c/i }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
