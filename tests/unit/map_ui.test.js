/**
 * tests/unit/map_ui.test.js
 * ─────────────────────────
 * Tests unitaires de www/map_ui.js.
 * Importe le VRAI module — plus de copie de fonctions.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  togglePanel,
  collapseOthers,
  enforceSinglePanel,
  initPanels,
  showPanel,
  isCompact,
  trackLayout,
  COMPACT_QUERY,
  REPO_URL,
  updateOsmLink,
  escapeHtml,
  buildDataPopupHtml,
} from '../../www/map_ui.js';

// ══════════════════════════════════════════════════════════
// togglePanel
// ══════════════════════════════════════════════════════════

describe('togglePanel', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="test-panel" class="panel">
        <div class="panel-content">contenu</div>
      </div>
    `;
  });

  it('ajoute la classe collapsed au premier clic', () => {
    togglePanel('test-panel');
    expect(document.getElementById('test-panel').classList.contains('collapsed')).toBe(true);
  });

  it('retire la classe collapsed au deuxième clic', () => {
    togglePanel('test-panel');
    togglePanel('test-panel');
    expect(document.getElementById('test-panel').classList.contains('collapsed')).toBe(false);
  });
});

const PANELS = `
  <div id="title-panel" class="panel"><div class="panel-content">t</div></div>
  <div id="levels-panel" class="panel" hidden><div class="panel-content">n</div></div>
  <div id="legend-panel" class="panel"><div class="panel-content">l</div></div>
`;
const isOpen = (id) => !document.getElementById(id).classList.contains('collapsed');
const fakeWindow = (matches) => {
  const listeners = [];
  return {
    listeners,
    matchMedia: (q) => ({ media: q, matches, addEventListener: (_, fn) => listeners.push(fn) }),
  };
};

describe('panneaux en mode compact', () => {
  beforeEach(() => {
    document.body.innerHTML = PANELS;
  });

  it('n’est jamais compact sans matchMedia', () => {
    expect(isCompact({})).toBe(false);
  });

  it('utilise la requête compacte', () => {
    let seen = null;
    isCompact({ matchMedia: (q) => { seen = q; return { matches: true }; } });
    expect(seen).toBe(COMPACT_QUERY);
  });

  it('laisse plusieurs panneaux ouverts hors mode compact', () => {
    togglePanel('legend-panel', false);
    togglePanel('legend-panel', false);
    expect(isOpen('title-panel')).toBe(true);
    expect(isOpen('legend-panel')).toBe(true);
  });

  it('referme les autres panneaux à l’ouverture en mode compact', () => {
    document.getElementById('legend-panel').classList.add('collapsed');
    togglePanel('legend-panel', true);
    expect(isOpen('legend-panel')).toBe(true);
    expect(isOpen('title-panel')).toBe(false);
  });

  it('ne touche pas aux autres panneaux à la fermeture', () => {
    document.getElementById('legend-panel').classList.add('collapsed');
    togglePanel('title-panel', true);
    expect(isOpen('title-panel')).toBe(false);
    expect(isOpen('legend-panel')).toBe(false);
  });

  it('ignore les panneaux masqués', () => {
    collapseOthers('legend-panel');
    expect(isOpen('levels-panel')).toBe(true);
    expect(isOpen('title-panel')).toBe(false);
  });

  it('enforceSinglePanel garde le premier panneau ouvert', () => {
    enforceSinglePanel();
    expect(isOpen('title-panel')).toBe(true);
    expect(isOpen('legend-panel')).toBe(false);
  });

  it('initPanels ne garde que le titre ouvert en mode compact', () => {
    initPanels(fakeWindow(true));
    expect(isOpen('title-panel')).toBe(true);
    expect(isOpen('levels-panel')).toBe(false);
    expect(isOpen('legend-panel')).toBe(false);
  });

  it('initPanels ne change rien sur grand écran', () => {
    initPanels(fakeWindow(false));
    expect(isOpen('levels-panel')).toBe(true);
    expect(isOpen('legend-panel')).toBe(true);
  });

  it('initPanels réduit à un panneau au passage en mode compact', () => {
    const win = fakeWindow(false);
    initPanels(win);
    win.listeners.forEach((fn) => fn({ matches: true }));
    expect(isOpen('title-panel')).toBe(true);
    expect(isOpen('legend-panel')).toBe(false);
  });

  it('showPanel affiche le panneau replié en mode compact', () => {
    showPanel('levels-panel', true, true);
    expect(document.getElementById('levels-panel').hidden).toBe(false);
    expect(isOpen('levels-panel')).toBe(false);
  });

  it('showPanel conserve l’état sur grand écran et sait masquer', () => {
    showPanel('levels-panel', true, false);
    expect(isOpen('levels-panel')).toBe(true);
    showPanel('levels-panel', false, false);
    expect(document.getElementById('levels-panel').hidden).toBe(true);
  });
});

describe('trackLayout', () => {
  it('publie la hauteur de l’attribution et des contrôles', () => {
    document.body.innerHTML = `
      <div id="m"><div class="maplibregl-ctrl-bottom-right">
        <div class="maplibregl-ctrl maplibregl-ctrl-attrib"></div>
      </div></div>`;
    const corner = document.querySelector('.maplibregl-ctrl-bottom-right');
    const attrib = document.querySelector('.maplibregl-ctrl-attrib');
    corner.getBoundingClientRect = () => ({ height: 180.2 });
    attrib.getBoundingClientRect = () => ({ height: 31.4 });
    const root = document.createElement('div');
    trackLayout(document.getElementById('m'), root);
    expect(root.style.getPropertyValue('--attrib-h')).toBe('32px');
    expect(root.style.getPropertyValue('--controls-h')).toBe('181px');
  });

  it('ne fait rien sans conteneur de contrôles', () => {
    document.body.innerHTML = '<div id="m"></div>';
    expect(trackLayout(document.getElementById('m'), document.createElement('div'))).toBeNull();
  });
});

describe('REPO_URL', () => {
  it('pointe vers le dépôt GitHub', () => {
    expect(REPO_URL).toBe('https://github.com/PasLoin/ZinnekeTiles');
  });
});

// ══════════════════════════════════════════════════════════
// updateOsmLink
// ══════════════════════════════════════════════════════════

describe('updateOsmLink', () => {
  beforeEach(() => {
    document.body.innerHTML = `<a id="osm-edit" class="osm-edit disabled" href="#">éditer</a>`;
  });

  it('active le lien quand zoom >= 16', () => {
    const map = {
      getZoom: () => 17,
      getCenter: () => ({ lat: 50.8503, lng: 4.3517 }),
    };
    updateOsmLink(map);

    const link = document.getElementById('osm-edit');
    expect(link.classList.contains('disabled')).toBe(false);
    expect(link.href).toContain('openstreetmap.org/edit');
    expect(link.href).toContain('50.85030');
    expect(link.href).toContain('4.35170');
  });

  it('désactive le lien quand zoom < 16', () => {
    const map = {
      getZoom: () => 14,
      getCenter: () => ({ lat: 50.8503, lng: 4.3517 }),
    };
    updateOsmLink(map);

    const link = document.getElementById('osm-edit');
    expect(link.classList.contains('disabled')).toBe(true);
    expect(link.href).toContain('#');
  });

  it('arrondit le zoom dans l\'URL', () => {
    const map = {
      getZoom: () => 17.6,
      getCenter: () => ({ lat: 50.0, lng: 4.0 }),
    };
    updateOsmLink(map);

    const link = document.getElementById('osm-edit');
    expect(link.href).toContain('#map=18/');
  });

  it('gère le zoom exact à 16', () => {
    const map = {
      getZoom: () => 16,
      getCenter: () => ({ lat: 50.0, lng: 4.0 }),
    };
    updateOsmLink(map);

    const link = document.getElementById('osm-edit');
    expect(link.classList.contains('disabled')).toBe(false);
  });
});

// ══════════════════════════════════════════════════════════
// escapeHtml
// ══════════════════════════════════════════════════════════

describe('escapeHtml', () => {
  it('échappe les balises HTML', () => {
    expect(escapeHtml('<script>alert("xss")</script>')).not.toContain('<script>');
    expect(escapeHtml('<b>bold</b>')).toBe('&lt;b&gt;bold&lt;/b&gt;');
  });

  it('échappe les guillemets et esperluettes', () => {
    expect(escapeHtml('a & b')).toBe('a &amp; b');
  });

  it('laisse passer le texte normal', () => {
    expect(escapeHtml('hello world')).toBe('hello world');
  });

  it('gère les chaînes vides', () => {
    expect(escapeHtml('')).toBe('');
  });
});

// ══════════════════════════════════════════════════════════
// buildDataPopupHtml
// ══════════════════════════════════════════════════════════

describe('buildDataPopupHtml', () => {
  it('affiche le layer ID et le source layer', () => {
    const feature = {
      layer: { id: 'buildings-fill' },
      sourceLayer: 'buildings',
      properties: { height: '10' },
    };
    const html = buildDataPopupHtml(feature);
    expect(html).toContain('buildings-fill');
    expect(html).toContain('(buildings)');
  });

  it('trie les propriétés par ordre alphabétique', () => {
    const feature = {
      layer: { id: 'test' },
      sourceLayer: 'src',
      properties: { z_index: '1', amenity: 'cafe', name: 'Chez Jo' },
    };
    const html = buildDataPopupHtml(feature);
    const keys = [...html.matchAll(/<th>([^<]+)<\/th>/g)].map(m => m[1]);
    expect(keys).toEqual(['amenity', 'name', 'z_index']);
  });

  it('échappe les valeurs HTML dans les propriétés (anti-XSS)', () => {
    const feature = {
      layer: { id: 'test' },
      sourceLayer: 'src',
      properties: { name: '<img src=x onerror=alert(1)>' },
    };
    const html = buildDataPopupHtml(feature);
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;img');
  });

  it('échappe les clés HTML dans les propriétés', () => {
    const feature = {
      layer: { id: 'test' },
      sourceLayer: 'src',
      properties: { '<script>': 'bad' },
    };
    const html = buildDataPopupHtml(feature);
    expect(html).not.toContain('<script>');
  });

  it('échappe aussi le layer ID et sourceLayer', () => {
    const feature = {
      layer: { id: '<b>bad</b>' },
      sourceLayer: '<i>evil</i>',
      properties: {},
    };
    const html = buildDataPopupHtml(feature);
    expect(html).not.toContain('<b>');
    expect(html).not.toContain('<i>');
  });

  it('gère sourceLayer absent', () => {
    const feature = {
      layer: { id: 'test' },
      properties: { a: '1' },
    };
    const html = buildDataPopupHtml(feature);
    // sourceLayer || '' → chaîne vide
    expect(html).toContain('test ()');
  });
});
