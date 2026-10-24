import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  PLAN_GROUP, GEO_TRANSIT_SOURCE, isPlanLayer, isGeoTransitLayer, hiddenByPlan,
  planAvailable, planLayerIds, geoTransitLayerIds, touchesTransit, isPlanSourceError,
} from '../../www/transit_plan.js';

const style = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../www/style.json'), 'utf8'));
const lazy = style.metadata['brussels:lazy'];
const html = fs.readFileSync(path.resolve(__dirname, '../../www/index.html'), 'utf8');

describe('style : plan octilinéaire', () => {
  it('déclare la source paresseuse du plan', () => {
    expect(lazy.sources[PLAN_GROUP].url).toBe(`./${PLAN_GROUP}.pmtiles.gz`);
    expect(style.sources[PLAN_GROUP]).toBeUndefined();
  });

  it('fournit les couches du plan, masquées par défaut', () => {
    const ids = planLayerIds(lazy);
    expect(ids).toEqual([
      'public_transport_octi-veil',
      'public_transport_octi-casing',
      'public_transport_octi-line',
      'public_transport_octi-station',
      'public_transport_octi-ref',
      'public_transport_octi-label',
    ]);
    for (const layer of lazy.layers.filter(isPlanLayer)) {
      expect(layer.layout.visibility).toBe('none');
    }
  });

  it('décale chaque ligne selon son rang dans le faisceau', () => {
    const line = lazy.layers.find((l) => l.id === 'public_transport_octi-line');
    expect(JSON.stringify(line.paint['line-offset'])).toContain('"slot"');
  });

  it('laisse la légende et la vue géographique inchangées', () => {
    const legendIds = style.metadata['brussels:legend'].map((g) => g.id);
    expect(legendIds).not.toContain(PLAN_GROUP);
    expect(geoTransitLayerIds(style.layers)).toEqual(expect.arrayContaining([
      'public_transport-casing', 'public_transport-line', 'public_transport-label',
    ]));
  });

  it('expose un bouton PLAN dans la page', () => {
    expect(html).toContain('id="toggle-plan"');
  });
});

describe('hiddenByPlan', () => {
  const plan = { id: 'public_transport_octi-line', metadata: { 'brussels:group': PLAN_GROUP } };
  const geo = { id: 'public_transport-line', source: GEO_TRANSIT_SOURCE };
  const other = { id: 'roads-primary', source: 'roads' };

  it('vue géographique : plan masqué, tracés visibles', () => {
    expect(hiddenByPlan(plan, false)).toBe(true);
    expect(hiddenByPlan(geo, false)).toBe(false);
  });

  it('mode plan : tracés masqués, plan visible', () => {
    expect(hiddenByPlan(plan, true)).toBe(false);
    expect(hiddenByPlan(geo, true)).toBe(true);
  });

  it('ignore les autres couches et les couches absentes', () => {
    expect(hiddenByPlan(other, true)).toBe(false);
    expect(hiddenByPlan(undefined, true)).toBe(false);
    expect(isGeoTransitLayer(null)).toBe(false);
  });
});

describe('utilitaires', () => {
  it('planAvailable', () => {
    expect(planAvailable(lazy)).toBe(true);
    expect(planAvailable(null)).toBe(false);
    expect(planAvailable({ sources: {}, layers: [] })).toBe(false);
  });

  it('touchesTransit', () => {
    expect(touchesTransit(['roads-primary', 'public_transport-line'], ['public_transport-line'])).toBe(true);
    expect(touchesTransit(['roads-primary'], ['public_transport-line'])).toBe(false);
    expect(touchesTransit(undefined, ['public_transport-line'])).toBe(false);
  });

  it('isPlanSourceError', () => {
    expect(isPlanSourceError({ sourceId: PLAN_GROUP })).toBe(true);
    expect(isPlanSourceError({ source: { id: PLAN_GROUP } })).toBe(true);
    expect(isPlanSourceError({ sourceId: 'roads' })).toBe(false);
    expect(isPlanSourceError(null)).toBe(false);
  });
});
