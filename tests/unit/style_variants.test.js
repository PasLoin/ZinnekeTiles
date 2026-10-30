import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  DEFAULT_STYLE_URL,
  MANIFEST_URL,
  requestedStyleId,
  manifestStyles,
  defaultStyleId,
  resolveStyle,
  styleHref,
  loadManifest,
  initStyleSelect,
} from '../../www/style_variants.js';

const MANIFEST = {
  default: 'default',
  styles: [
    { id: 'default', label: 'Standard', url: 'style.json' },
    { id: 'nb', label: 'Noir et blanc', url: 'style.nb.json' },
  ],
};

describe('requestedStyleId', () => {
  it('lit le paramètre style', () => {
    expect(requestedStyleId('?style=nb')).toBe('nb');
    expect(requestedStyleId('?a=1&style=nb')).toBe('nb');
  });

  it('renvoie null sans paramètre', () => {
    expect(requestedStyleId('')).toBeNull();
    expect(requestedStyleId(undefined)).toBeNull();
  });
});

describe('manifestStyles / defaultStyleId', () => {
  it('ignore les entrées incomplètes', () => {
    const styles = manifestStyles({ styles: [null, { id: 'a' }, { url: 'x' }, { id: 'b', url: 'b.json' }] });
    expect(styles.map((s) => s.id)).toEqual(['b']);
  });

  it('tolère un manifeste absent ou malformé', () => {
    expect(manifestStyles(null)).toEqual([]);
    expect(manifestStyles({ styles: 'nope' })).toEqual([]);
    expect(defaultStyleId(null)).toBe('default');
    expect(defaultStyleId({ default: 'nb' })).toBe('nb');
  });
});

describe('resolveStyle', () => {
  it('choisit la variante demandée', () => {
    expect(resolveStyle(MANIFEST, 'nb')).toEqual({ id: 'nb', url: './style.nb.json' });
  });

  it('retombe sur le style par défaut pour un identifiant inconnu', () => {
    expect(resolveStyle(MANIFEST, 'inconnu')).toEqual({ id: 'default', url: './style.json' });
    expect(resolveStyle(MANIFEST, null)).toEqual({ id: 'default', url: './style.json' });
  });

  it('retombe sur style.json sans manifeste', () => {
    expect(resolveStyle(null, 'nb')).toEqual({ id: 'default', url: DEFAULT_STYLE_URL });
  });

  it('normalise les URL relatives', () => {
    const m = { styles: [{ id: 'default', url: './style.json' }, { id: 'x', url: '/style.x.json' }] };
    expect(resolveStyle(m, 'default').url).toBe('./style.json');
    expect(resolveStyle(m, 'x').url).toBe('./style.x.json');
  });
});

describe('styleHref', () => {
  it('ajoute le paramètre et conserve le hash de position', () => {
    const href = styleHref('https://ex.org/map/#14/50.85/4.35', 'nb');
    expect(href).toBe('https://ex.org/map/?style=nb#14/50.85/4.35');
  });

  it('retire le paramètre pour le style par défaut', () => {
    expect(styleHref('https://ex.org/map/?style=nb#14/50.85/4.35', 'default'))
      .toBe('https://ex.org/map/#14/50.85/4.35');
  });

  it('conserve les autres paramètres', () => {
    expect(styleHref('https://ex.org/?debug=1', 'nb')).toBe('https://ex.org/?debug=1&style=nb');
  });
});

describe('loadManifest', () => {
  it('charge styles.json', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, json: async () => MANIFEST });
    expect(await loadManifest(fetchFn)).toEqual(MANIFEST);
    expect(fetchFn).toHaveBeenCalledWith(MANIFEST_URL);
  });

  it('renvoie null si le manifeste est absent', async () => {
    expect(await loadManifest(vi.fn().mockResolvedValue({ ok: false }))).toBeNull();
  });

  it('renvoie null en cas d’erreur réseau ou de JSON invalide', async () => {
    expect(await loadManifest(vi.fn().mockRejectedValue(new Error('offline')))).toBeNull();
    const bad = { ok: true, json: async () => { throw new SyntaxError('bad'); } };
    expect(await loadManifest(vi.fn().mockResolvedValue(bad))).toBeNull();
  });
});

describe('initStyleSelect', () => {
  it('remplit le sélecteur et marque le style courant', () => {
    const select = document.createElement('select');
    select.hidden = true;
    expect(initStyleSelect(select, MANIFEST, 'nb', () => {})).toBe(true);
    expect(select.hidden).toBe(false);
    expect([...select.options].map((o) => [o.value, o.textContent])).toEqual([
      ['default', 'Standard'],
      ['nb', 'Noir et blanc'],
    ]);
    expect(select.value).toBe('nb');
  });

  it('appelle onPick au changement', () => {
    const select = document.createElement('select');
    const onPick = vi.fn();
    initStyleSelect(select, MANIFEST, 'default', onPick);
    select.value = 'nb';
    select.dispatchEvent(new Event('change'));
    expect(onPick).toHaveBeenCalledWith('nb');
  });

  it('reste masqué avec un seul style ou sans manifeste', () => {
    const select = document.createElement('select');
    expect(initStyleSelect(select, { styles: [MANIFEST.styles[0]] }, 'default', () => {})).toBe(false);
    expect(select.hidden).toBe(true);
    expect(initStyleSelect(select, null, 'default', () => {})).toBe(false);
    expect(initStyleSelect(null, MANIFEST, 'default', () => {})).toBe(false);
  });
});

describe('Variantes générées', () => {
  const www = path.resolve(__dirname, '../../www');
  const manifestPath = path.join(www, 'styles.json');
  const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, 'utf8')) : null;

  it.skipIf(!manifest)('chaque entrée du manifeste pointe vers un style existant', () => {
    for (const entry of manifestStyles(manifest)) {
      const style = JSON.parse(fs.readFileSync(path.join(www, entry.url), 'utf8'));
      expect(style.version).toBe(8);
      if (entry.id !== defaultStyleId(manifest)) {
        expect(style.metadata['brussels:variant'].id).toBe(entry.id);
      }
    }
  });
});
