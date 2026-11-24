import { expect, test } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const out = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/screenshots')

async function signIn(page: import('@playwright/test').Page) {
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'domcontentloaded' })
  await page.locator('input[type="email"]').fill('demo@travelgraph.local')
  await page.locator('input[type="password"]').fill('TravelGraphDemo!2026')
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL(/dashboard|explore/, { timeout: 20000 })
}

test.describe('Terra visual smoke', () => {
  test('desktop terra surfaces', async ({ page }) => {
    test.setTimeout(180_000)
    await page.setViewportSize({ width: 1440, height: 900 })

    await page.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: /somewhere new/i })).toBeVisible({ timeout: 20000 })
    await page.waitForTimeout(800)
    await page.screenshot({ path: path.join(out, 'terra-landing-desktop.png'), fullPage: true })

    await signIn(page)

    await page.goto('http://127.0.0.1:5173/explore', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: /^explore$/i })).toBeVisible({ timeout: 20000 })
    await page.locator('#explore-query').fill('quiet hills and waterfalls')
    await page.getByRole('button', { name: /^search$/i }).click()
    await page.waitForTimeout(2500)
    await page.screenshot({ path: path.join(out, 'terra-explore-desktop.png'), fullPage: true })

    await page.goto('http://127.0.0.1:5173/destinations/sohra', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: /sohra/i })).toBeVisible({ timeout: 20000 })
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(out, 'terra-destination-desktop.png'), fullPage: true })

    await page.goto('http://127.0.0.1:5173/explore/map', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: /^map$/i })).toBeVisible({ timeout: 20000 })
    await page.waitForTimeout(1500)
    await page.screenshot({ path: path.join(out, 'terra-map-desktop.png'), fullPage: true })

    await page.goto('http://127.0.0.1:5173/intelligence/knowledge', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: /knowledge explorer/i })).toBeVisible({ timeout: 20000 })
    await page.waitForTimeout(1500)
    await page.screenshot({ path: path.join(out, 'terra-knowledge-desktop.png'), fullPage: true })
  })

  test('mobile terra landing and explore', async ({ page }) => {
    test.setTimeout(120_000)
    await page.setViewportSize({ width: 390, height: 844 })

    await page.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: /somewhere new/i })).toBeVisible({ timeout: 20000 })
    await page.waitForTimeout(800)
    await page.screenshot({ path: path.join(out, 'terra-landing-mobile.png'), fullPage: true })

    await signIn(page)
    await page.goto('http://127.0.0.1:5173/explore', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: /^explore$/i })).toBeVisible({ timeout: 20000 })
    await page.waitForTimeout(1200)
    await page.screenshot({ path: path.join(out, 'terra-explore-mobile.png'), fullPage: true })
  })
})
