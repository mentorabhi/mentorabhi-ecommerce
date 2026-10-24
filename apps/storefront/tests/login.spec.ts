import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function localCatalogAdminPassword(): string {
  const path = resolve(import.meta.dirname, '../../../devops/.local/bootstrap.env')
  const value = readFileSync(path, 'utf8')
    .split(/\r?\n/)
    .find((line) => line.startsWith('DEMO_CATALOG_ADMIN_PASSWORD='))
    ?.slice('DEMO_CATALOG_ADMIN_PASSWORD='.length)
  if (!value) throw new Error('Run devops/scripts/supersports configure before the local login regression.')
  return value
}

test('catalog admin stays rendered after local Keycloak login', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))

  await page.goto('/')
  await page.getByRole('button', { name: /sign in with local account/i }).click()
  await page.locator('input[name="username"]').fill('catalog-admin')
  await page.locator('input[name="password"]').fill(localCatalogAdminPassword())
  await page.locator('input[name="password"]').press('Enter')

  const outcome = await Promise.race([
    page.locator('.app-shell').waitFor({ state: 'visible', timeout: 20_000 }).then(() => 'workspace rendered'),
    page.waitForEvent('pageerror').then((error) => `browser error: ${error.message}`),
  ])
  expect(outcome).toBe('workspace rendered')
  await expect(page.getByRole('navigation', { name: 'Workspace sections' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Catalog.' })).toBeVisible()
  await expect(page.getByText('Pro Willow Cricket Bat')).toBeVisible()
  expect(pageErrors).toEqual([])
})
