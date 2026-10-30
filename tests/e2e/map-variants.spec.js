import { test, expect } from '@playwright/test';

async function waitForStyle(page) {
  await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
  await page.waitForFunction(
    () => window.map && typeof window.map.getStyle === 'function' && window.map.isStyleLoaded(),
    { timeout: 20_000 }
  );
}

const variantId = (page) =>
  page.evaluate(() => (window.map.getStyle().metadata['brussels:variant'] || {}).id || 'default');

test.describe('Variantes de style', () => {
  test('le sélecteur liste les styles du manifeste', async ({ page, request }) => {
    const manifest = await (await request.get('/styles.json')).json();
    await page.goto('/');
    await waitForStyle(page);
    const select = page.locator('#style-select');
    await expect(select).toBeVisible();
    await expect(select.locator('option')).toHaveCount(manifest.styles.length);
    await expect(select).toHaveValue('default');
    expect(await variantId(page)).toBe('default');
  });

  test('?style=nb charge la variante noir et blanc', async ({ page }) => {
    await page.goto('/?style=nb');
    await waitForStyle(page);
    expect(await variantId(page)).toBe('nb');
    await expect(page.locator('#style-select')).toHaveValue('nb');
    const sources = await page.evaluate(() => Object.keys(window.map.getStyle().sources));
    expect(sources).not.toContain('poi');
  });

  test('un identifiant inconnu retombe sur le style par défaut', async ({ page }) => {
    await page.goto('/?style=inexistant');
    await waitForStyle(page);
    expect(await variantId(page)).toBe('default');
  });

  test('changer de style recharge la page en gardant la position', async ({ page }) => {
    await page.goto('/#15/50.8466/4.3528');
    await waitForStyle(page);
    await Promise.all([
      page.waitForURL(/\?style=nb#15\/50\.8466\/4\.3528/),
      page.locator('#style-select').selectOption('nb'),
    ]);
    await waitForStyle(page);
    expect(await variantId(page)).toBe('nb');
  });

  test('sans manifeste, le sélecteur reste masqué et style.json est chargé', async ({ page }) => {
    await page.route('**/styles.json', (route) => route.fulfill({ status: 404, body: 'Not Found' }));
    await page.goto('/?style=nb');
    await waitForStyle(page);
    await expect(page.locator('#style-select')).toBeHidden();
    expect(await variantId(page)).toBe('default');
  });
});
