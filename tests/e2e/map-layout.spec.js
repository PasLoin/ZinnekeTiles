import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'petit téléphone', width: 360, height: 640 },
  { name: 'iPhone SE', width: 375, height: 667 },
  { name: 'Pixel 5', width: 393, height: 851 },
  { name: 'téléphone paysage', width: 740, height: 360 },
  { name: 'tablette', width: 820, height: 1180 },
  { name: 'ordinateur', width: 1280, height: 720 },
];

async function uiBoxes(page) {
  return page.evaluate(() => {
    const pick = [
      ['titre', '#title-panel'],
      ['niveaux', '#levels-panel'],
      ['légende', '#legend-panel'],
      ['boutons', '.view-toggle'],
    ];
    const boxes = [];
    const visible = (el) => el && !el.hidden && getComputedStyle(el).display !== 'none';
    for (const [name, sel] of pick) {
      const el = document.querySelector(sel);
      if (visible(el)) boxes.push({ name, ...el.getBoundingClientRect().toJSON() });
    }
    document.querySelectorAll('.maplibregl-ctrl-bottom-right > .maplibregl-ctrl').forEach((el, i) => {
      if (visible(el)) boxes.push({ name: `contrôle ${i} (${el.className})`, ...el.getBoundingClientRect().toJSON() });
    });
    return boxes;
  });
}

function overlaps(boxes) {
  const hits = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i];
      const b = boxes[j];
      const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (x > 1 && y > 1) hits.push(`${a.name} ↔ ${b.name}`);
    }
  }
  return hits;
}

function outside(boxes, { width, height }) {
  return boxes
    .filter((b) => b.left < -1 || b.top < -1 || b.right > width + 1 || b.bottom > height + 1)
    .map((b) => b.name);
}

async function expectClean(page, viewport, label) {
  await page.waitForTimeout(400);
  const boxes = await uiBoxes(page);
  expect(overlaps(boxes), `${label} : chevauchements`).toEqual([]);
  expect(outside(boxes, viewport), `${label} : hors écran`).toEqual([]);
}

async function expand(page, id) {
  const panel = page.locator(`#${id}`);
  if (/collapsed/.test(await panel.getAttribute('class'))) {
    await panel.locator('.panel-header .toggle-icon').click();
  }
}

for (const viewport of VIEWPORTS) {
  test.describe(`Mise en page — ${viewport.name} ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });

    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await page.waitForSelector('.legend-row', { state: 'attached', timeout: 30_000 });
    });

    test('aucun élément ne se chevauche, en 2D comme en 3D', async ({ page }) => {
      await expectClean(page, viewport, '2D au démarrage');

      await expand(page, 'legend-panel');
      await expectClean(page, viewport, '2D légende ouverte');

      await page.click('#toggle-3d');
      await expect(page.locator('#levels-panel')).toBeVisible();
      await expectClean(page, viewport, '3D');

      await expand(page, 'levels-panel');
      await page.locator('#levels-panel input[value="select"]').check();
      await expectClean(page, viewport, '3D niveaux ouverts');

      await expand(page, 'legend-panel');
      await expectClean(page, viewport, '3D légende ouverte');

      await expand(page, 'title-panel');
      await expectClean(page, viewport, '3D titre ouvert');
    });
  });
}

test.describe('Mode compact', () => {
  test.use({ viewport: { width: 375, height: 667 }, deviceScaleFactor: 1 });

  test('un seul panneau ouvert à la fois', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.legend-row', { state: 'attached', timeout: 30_000 });
    await expect(page.locator('#legend-panel')).toHaveClass(/collapsed/);
    await expect(page.locator('#title-panel')).not.toHaveClass(/collapsed/);

    await page.locator('#legend-panel .panel-header .toggle-icon').click();
    await expect(page.locator('#legend-panel')).not.toHaveClass(/collapsed/);
    await expect(page.locator('#title-panel')).toHaveClass(/collapsed/);
  });
});
