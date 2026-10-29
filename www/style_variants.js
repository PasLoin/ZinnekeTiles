export const DEFAULT_STYLE_ID = 'default';
export const DEFAULT_STYLE_URL = './style.json';
export const MANIFEST_URL = './styles.json';
export const STYLE_PARAM = 'style';

export function requestedStyleId(search) {
  return new URLSearchParams(search || '').get(STYLE_PARAM);
}

export function manifestStyles(manifest) {
  const styles = manifest && Array.isArray(manifest.styles) ? manifest.styles : [];
  return styles.filter((s) => s && typeof s.id === 'string' && typeof s.url === 'string');
}

export function defaultStyleId(manifest) {
  return (manifest && typeof manifest.default === 'string' && manifest.default) || DEFAULT_STYLE_ID;
}

export function resolveStyle(manifest, id) {
  const styles = manifestStyles(manifest);
  const fallback = defaultStyleId(manifest);
  const entry = styles.find((s) => s.id === id) || styles.find((s) => s.id === fallback);
  if (!entry) return { id: fallback, url: DEFAULT_STYLE_URL };
  return { id: entry.id, url: './' + entry.url.replace(/^\.?\//, '') };
}

export function styleHref(href, id, fallback = DEFAULT_STYLE_ID) {
  const url = new URL(href);
  if (!id || id === fallback) url.searchParams.delete(STYLE_PARAM);
  else url.searchParams.set(STYLE_PARAM, id);
  return url.href;
}

export async function loadManifest(fetchFn = globalThis.fetch) {
  try {
    const res = await fetchFn(MANIFEST_URL);
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

export function initStyleSelect(select, manifest, currentId, onPick) {
  if (!select) return false;
  const styles = manifestStyles(manifest);
  if (styles.length < 2) {
    select.hidden = true;
    return false;
  }
  select.replaceChildren(...styles.map((s) => {
    const option = document.createElement('option');
    option.value = s.id;
    option.textContent = s.label || s.id;
    option.selected = s.id === currentId;
    return option;
  }));
  select.hidden = false;
  select.addEventListener('change', () => onPick(select.value));
  return true;
}
