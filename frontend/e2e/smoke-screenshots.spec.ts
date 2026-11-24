import { expect, test } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const out = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/screenshots')

test.describe('TravelGraph visual smoke', () => {
  test('login + dashboard + studio desktop', async ({ page }) => {
    test.setTimeout(120_000)
    const go = (url: string) => page.goto(url, { waitUntil: 'domcontentloaded' })
    await page.setViewportSize({ width: 1440, height: 900 })
    await go('http://127.0.0.1:5173/login')
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible({ timeout: 20000 })
    await page.screenshot({ path: path.join(out, 'login-desktop.png'), fullPage: true })

    await page.locator('input[type="email"]').fill('demo@travelgraph.local')
    await page.locator('input[type="password"]').fill('TravelGraphDemo!2026')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/dashboard/, { timeout: 20000 })
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(out, 'dashboard-desktop.png'), fullPage: true })

    await go('http://127.0.0.1:5173/trips')
    await expect(page.getByText(/my journeys/i)).toBeVisible({ timeout: 20000 })
    await page.screenshot({ path: path.join(out, 'trips-desktop.png'), fullPage: true })

    await go('http://127.0.0.1:5173/studio')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: path.join(out, 'studio-desktop.png'), fullPage: true })

    await go('http://127.0.0.1:5173/costs')
    await page.waitForTimeout(1500)
    await page.screenshot({ path: path.join(out, 'costs-desktop.png'), fullPage: true })
  })

  test('mobile dashboard', async ({ page }) => {
    test.setTimeout(90_000)
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'domcontentloaded' })
    await page.locator('input[type="email"]').fill('demo@travelgraph.local')
    await page.locator('input[type="password"]').fill('TravelGraphDemo!2026')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/dashboard/, { timeout: 20000 })
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(out, 'dashboard-mobile.png'), fullPage: true })
  })
})
