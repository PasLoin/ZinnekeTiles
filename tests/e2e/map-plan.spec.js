import { test, expect } from '@playwright/test';

const PLAN_LINE = 'public_transport_octi-line';
const GEO_LINE = 'public_transport-line';

test.describe('Plan octilinéaire STIB', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('canvas.maplibregl-canvas', { timeout: 15_000 });
    await page.waitForFunction(
      () => window.map && window.map.isStyleLoaded(),
      { timeout: 20_000 }
    );
    await page.waitForSelector('#legend-content .legend-row', { timeout: 10_000 });
  });

  test('la vue géographique est affichée par défaut', async ({ page }) => {
    const btn = page.locator('#toggle-plan');
    await expect(btn).toBeVisible();
    await expect(btn).toHaveAttribute('aria-pressed', 'false');
    const state = await page.evaluate(([plan, geo]) => ({
      plan: window.map.getLayer(plan) ? window.map.getLayoutProperty(plan, 'visibility') : 'absent',
      geo: window.map.getLayoutProperty(geo, 'visibility') ?? 'visible',
    }), [PLAN_LINE, GEO_LINE]);
    expect(['absent', 'none']).toContain(state.plan);
    expect(state.geo).toBe('visible');
  });

  test('le bouton PLAN bascule entre les deux représentations', async ({ page }) => {
    const btn = page.locator('#toggle-plan');
    await btn.click();

    await page.waitForFunction(([plan, geo]) => {
      const b = document.getElementById('toggle-plan');
      if (b.disabled) return true;
      return b.getAttribute('aria-pressed') === 'true'
        && !!window.map.getLayer(plan)
        && window.map.getLayoutProperty(plan, 'visibility') === 'visible'
        && window.map.getLayoutProperty(geo, 'visibility') === 'none';
    }, [PLAN_LINE, GEO_LINE], { timeout: 10_000 });

    test.skip(await btn.isDisabled(), 'public_transport_octi.pmtiles.gz absent de www/');

    const top = await page.evaluate(() => window.map.getStyle().layers.at(-1).id);
    expect(top).toBe('public_transport_octi-label');

    await btn.click();
    await expect(btn).toHaveAttribute('aria-pressed', 'false');
    const after = await page.evaluate(([plan, geo]) => ({
      plan: window.map.getLayoutProperty(plan, 'visibility'),
      geo: window.map.getLayoutProperty(geo, 'visibility'),
    }), [PLAN_LINE, GEO_LINE]);
    expect(after.plan).toBe('none');
    expect(after.geo).toBe('visible');
  });
});
