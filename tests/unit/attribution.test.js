import { describe, it, expect } from 'vitest';
import { buildAttribution, formatUtcDate } from '../../www/map_ui.js';

const DATA = {
  timestamp: '2026-09-01T05:27:29Z',
  sha256: 'a10eb5deacbf',
  generated_at: '2026-09-01T06:02:00Z',
};

describe('formatUtcDate', () => {
  it('formate une date ISO en UTC', () => {
    expect(formatUtcDate('2026-09-01T05:27:29Z')).toBe('01/09/2026 05:27 UTC');
  });

  it('retourne null pour une valeur absente ou invalide', () => {
    expect(formatUtcDate(null)).toBeNull();
    expect(formatUtcDate('pas une date')).toBeNull();
  });
});

describe('buildAttribution', () => {
  it('affiche la date des données et la date de mise à jour', () => {
    expect(buildAttribution(DATA))
      .toBe('Données 01/09/2026 05:27 UTC · Mise à jour 01/09/2026 06:02 UTC');
  });

  it('n’affiche ni hash ni version de config', () => {
    const txt = buildAttribution(DATA);
    expect(txt).not.toContain('a10eb5deacbf');
    expect(txt).not.toContain('Config');
    expect(txt).not.toContain('seq');
  });

  it('préfère le timestamp de réplication pour la date des données', () => {
    const data = { ...DATA, replication_timestamp: '2026-09-02T00:00:00Z', replication_sequence: 4242 };
    expect(buildAttribution(data))
      .toBe('Données 02/09/2026 00:00 UTC · Mise à jour 01/09/2026 06:02 UTC');
  });

  it('omet la partie dont la date est absente ou invalide', () => {
    expect(buildAttribution({ timestamp: DATA.timestamp })).toBe('Données 01/09/2026 05:27 UTC');
    expect(buildAttribution({ generated_at: DATA.generated_at })).toBe('Mise à jour 01/09/2026 06:02 UTC');
    expect(buildAttribution({ timestamp: 'x', generated_at: 'y' })).toBeNull();
  });

  it('retourne null sans data-info', () => {
    expect(buildAttribution(null)).toBeNull();
    expect(buildAttribution(undefined)).toBeNull();
  });
});
