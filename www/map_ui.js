/**
 * map_ui.js
 * ─────────
 * Fonctions UI réutilisables de la carte Brussels.
 * Importé par index.html et par les tests unitaires.
 */

export const REPO_URL = 'https://github.com/PasLoin/ZinnekeTiles';
export const COMPACT_QUERY = '(max-width: 600px), (max-height: 500px)';
export const MAIN_PANEL = 'title-panel';

export function isCompact(win = globalThis) {
  return typeof win.matchMedia === 'function' && win.matchMedia(COMPACT_QUERY).matches;
}

function shownPanels() {
  return [...document.querySelectorAll('.panel')].filter((p) => !p.hidden);
}

export function collapseOthers(id) {
  for (const panel of shownPanels()) {
    if (panel.id !== id) panel.classList.add('collapsed');
  }
}

export function togglePanel(id, compact = isCompact()) {
  const collapsed = document.getElementById(id).classList.toggle('collapsed');
  if (!collapsed && compact) collapseOthers(id);
}

export function enforceSinglePanel() {
  const open = shownPanels().filter((p) => !p.classList.contains('collapsed'));
  if (open.length > 1) collapseOthers(open[0].id);
}

export function initPanels(win = globalThis) {
  if (isCompact(win)) {
    for (const panel of document.querySelectorAll('.panel')) {
      if (panel.id !== MAIN_PANEL) panel.classList.add('collapsed');
    }
  }
  if (typeof win.matchMedia !== 'function') return;
  const query = win.matchMedia(COMPACT_QUERY);
  if (typeof query.addEventListener === 'function') {
    query.addEventListener('change', (e) => { if (e.matches) enforceSinglePanel(); });
  }
}

export function showPanel(id, shown, compact = isCompact()) {
  const panel = document.getElementById(id);
  if (shown && panel.hidden && compact) panel.classList.add('collapsed');
  panel.hidden = !shown;
}

export function trackLayout(container, root = document.documentElement) {
  const corner = container.querySelector('.maplibregl-ctrl-bottom-right');
  if (!corner) return null;
  const update = () => {
    const attrib = corner.querySelector('.maplibregl-ctrl-attrib');
    const attribH = attrib ? attrib.getBoundingClientRect().height : 0;
    root.style.setProperty('--attrib-h', `${Math.ceil(attribH)}px`);
    root.style.setProperty('--controls-h', `${Math.ceil(corner.getBoundingClientRect().height)}px`);
  };
  update();
  if (typeof ResizeObserver !== 'function') return null;
  const observer = new ResizeObserver(update);
  observer.observe(corner);
  for (const ctrl of corner.children) observer.observe(ctrl);
  return observer;
}

/**
 * Met à jour le lien « éditer dans OpenStreetMap ».
 * Actif uniquement à zoom ≥ 16.
 * @param {object} map - Instance MapLibre GL (getZoom, getCenter)
 */
export function updateOsmLink(map) {
  const link = document.getElementById('osm-edit');
  const zoom = map.getZoom();
  const center = map.getCenter();

  if (zoom >= 16) {
    link.classList.remove('disabled');
    link.href = `https://www.openstreetmap.org/edit#map=${Math.round(zoom)}/${center.lat.toFixed(5)}/${center.lng.toFixed(5)}`;
  } else {
    link.classList.add('disabled');
    link.href = '#';
  }
}

/**
 * Échappe le HTML pour éviter les injections XSS dans le popup DATA.
 * @param {string} str
 * @returns {string}
 */
export function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Construit le HTML du popup DATA à partir d'une feature MapLibre.
 * @param {object} feature - Feature retournée par queryRenderedFeatures
 * @returns {string} HTML sécurisé
 */
export function buildDataPopupHtml(feature) {
  const props = feature.properties;
  const layerId = escapeHtml(String(feature.layer.id));
  const sourceLayer = escapeHtml(String(feature.sourceLayer || ''));

  let html = `<div class="layer-info">${layerId} (${sourceLayer})</div><table>`;
  const sortedKeys = Object.keys(props).sort();
  for (const key of sortedKeys) {
    html += `<tr><th>${escapeHtml(String(key))}</th><td>${escapeHtml(String(props[key]))}</td></tr>`;
  }
  html += `</table>`;
  return html;
}

export function formatUtcDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getUTCDate())}/${p(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())} UTC`;
}

export function buildAttribution(dataInfo) {
  if (!dataInfo) return null;
  const parts = [];
  const data = formatUtcDate(dataInfo.replication_timestamp || dataInfo.timestamp);
  const updated = formatUtcDate(dataInfo.generated_at);
  if (data) parts.push(`Données ${data}`);
  if (updated) parts.push(`Mise à jour ${updated}`);
  return parts.length ? escapeHtml(parts.join(' · ')) : null;
}
