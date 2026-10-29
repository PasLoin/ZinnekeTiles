/**
 * tests/e2e/map-load.spec.js
 * ──────────────────────────
 * Tests E2E : chargement de la carte, panneaux, contrôles de base.
 */
import { test, expect } from '@playwright/test';

test.describe('Chargement de la carte', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Attendre que le canvas MapLibre soit rendu
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
  });

  test('la page se charge sans erreur console critique', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));

    // Recharger pour capturer les erreurs dès le début
    await page.reload();
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });

    // Filtrer : ignorer les erreurs réseau (PMTiles absents en test)
    const critical = errors.filter(
      (e) => !e.includes('pmtiles') && !e.includes('fetch') && !e.includes('404')
    );
    expect(critical).toHaveLength(0);
  });

  test('le canvas MapLibre est visible', async ({ page }) => {
    const canvas = page.locator('canvas.maplibregl-canvas');
    await expect(canvas).toBeVisible();
    // Vérifier que le canvas a des dimensions raisonnables
    const box = await canvas.boundingBox();
    expect(box.width).toBeGreaterThan(100);
    expect(box.height).toBeGreaterThan(100);
  });

  test('le titre "ZinnekeTiles" renvoie vers le dépôt GitHub', async ({ page }) => {
    const link = page.locator('#title-panel h1 a');
    await expect(link).toHaveText('ZinnekeTiles');
    await expect(link).toHaveAttribute('href', 'https://github.com/PasLoin/ZinnekeTiles');
    await expect(link).toHaveAttribute('target', '_blank');
  });

  test('cliquer sur le titre ne replie pas le panneau', async ({ page, context }) => {
    await context.route('https://github.com/**', (route) => route.fulfill({ status: 200, body: '' }));
    const panel = page.locator('#title-panel');
    const before = await panel.getAttribute('class');
    const popup = context.waitForEvent('page');
    await page.locator('#title-panel h1 a').click();
    await (await popup).close();
    await expect(panel).toHaveAttribute('class', before);
  });

  test('le sous-titre mentionne OpenStreetMap', async ({ page }) => {
    const subtitle = page.locator('#title-panel p');
    await expect(subtitle).toContainText('OpenStreetMap');
  });
});

test.describe('Panneau titre', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
  });

  test('se replie au clic sur le header', async ({ page }) => {
    const panel = page.locator('#title-panel');
    const toggle = panel.locator('.panel-header .toggle-icon');
    const content = panel.locator('.panel-content');

    await expect(content).toBeVisible();
    await toggle.click();
    await expect(panel).toHaveClass(/collapsed/);
    await expect(content).toBeHidden();
  });

  test('se déplie au second clic', async ({ page }) => {
    const panel = page.locator('#title-panel');
    const toggle = panel.locator('.panel-header .toggle-icon');

    await toggle.click();
    await expect(panel).toHaveClass(/collapsed/);
    await toggle.click();
    await expect(panel).not.toHaveClass(/collapsed/);
  });
});

test.describe('Panneau légende', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
  });

  test('est présent et contient le titre "Légende"', async ({ page }) => {
    const legend = page.locator('#legend-panel h2');
    await expect(legend).toHaveText('Légende');
  });

  test('se replie et se déplie', async ({ page }) => {
    const panel = page.locator('#legend-panel');
    const header = panel.locator('.panel-header');
    const wasCollapsed = /collapsed/.test(await panel.getAttribute('class'));

    await header.click();
    await expect(panel).toHaveClass(wasCollapsed ? /^(?!.*collapsed)/ : /collapsed/);

    await header.click();
    await expect(panel).toHaveClass(wasCollapsed ? /collapsed/ : /^(?!.*collapsed)/);
  });
});

test.describe('Contrôles de vue', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
  });

  test('le bouton 3D est présent et affiche "MODE 3D"', async ({ page }) => {
    const btn = page.locator('#toggle-3d');
    await expect(btn).toHaveText('MODE 3D');
  });

  test('le bouton DATA est présent', async ({ page }) => {
    const btn = page.locator('#toggle-data');
    await expect(btn).toHaveText('DATA');
  });

  test('le bouton 3D bascule le texte en "MODE 2D" au clic', async ({ page }) => {
    const btn = page.locator('#toggle-3d');
    await btn.click();
    await expect(btn).toHaveText('MODE 2D');
  });

  test('le bouton 3D revient à "MODE 3D" au deuxième clic', async ({ page }) => {
    const btn = page.locator('#toggle-3d');
    await btn.click();
    await btn.click();
    await expect(btn).toHaveText('MODE 3D');
  });

  test('le bouton DATA active le mode data (classe active)', async ({ page }) => {
    const btn = page.locator('#toggle-data');
    await btn.click();
    await expect(btn).toHaveClass(/active/);
  });

  test('le bouton DATA change le curseur en crosshair', async ({ page }) => {
    const btn = page.locator('#toggle-data');
    await btn.click();

    const canvas = page.locator('canvas.maplibregl-canvas');
    const cursor = await canvas.evaluate((el) => el.style.cursor);
    expect(cursor).toBe('crosshair');
  });
});

test.describe('Lien OSM', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
  });

  test('le lien d\'édition OSM est présent', async ({ page }) => {
    const link = page.locator('#osm-edit');
    await expect(link).toBeVisible();
  });

  test('le lien est désactivé au zoom initial (13)', async ({ page }) => {
    const link = page.locator('#osm-edit');
    await expect(link).toHaveClass(/disabled/);
  });
});

test.describe('Contrôles MapLibre', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
  });

  test('le contrôle de zoom est présent', async ({ page }) => {
    const zoomIn = page.locator('.maplibregl-ctrl-zoom-in');
    await expect(zoomIn).toBeVisible();
  });

  test('le contrôle d\'inclinaison incline puis redresse la vue', async ({ page }) => {
    const up = page.locator('.pitch-ctrl .pitch-up');
    const down = page.locator('.pitch-ctrl .pitch-down');
    await expect(up).toBeVisible();
    await expect(down).toBeDisabled();
    await up.click();
    await expect.poll(() => page.evaluate(() => Math.round(window.map.getPitch()))).toBe(15);
    await expect(down).toBeEnabled();
    await down.click();
    await expect.poll(() => page.evaluate(() => Math.round(window.map.getPitch()))).toBe(0);
  });

  test('le contrôle d\'échelle est présent', async ({ page }) => {
    const scale = page.locator('.maplibregl-ctrl-scale');
    await expect(scale).toBeVisible();
  });
});
