import { lazyLayersOf } from './indoor.js';

export const PLAN_GROUP = 'public_transport_octi';
export const GEO_TRANSIT_SOURCE = 'public_transport';

export function isPlanLayer(layer) {
  return !!layer && ((layer.metadata || {})['brussels:group']) === PLAN_GROUP;
}

export function isGeoTransitLayer(layer) {
  return !!layer && layer.source === GEO_TRANSIT_SOURCE;
}

export function hiddenByPlan(layer, planOn) {
  if (isPlanLayer(layer)) return !planOn;
  if (isGeoTransitLayer(layer)) return !!planOn;
  return false;
}

export function planAvailable(lazy) {
  return !!(lazy && lazy.sources && lazy.sources[PLAN_GROUP]) && planLayerIds(lazy).length > 0;
}

export function planLayerIds(lazy) {
  return lazyLayersOf(lazy, PLAN_GROUP).map((layer) => layer.id);
}

export function geoTransitLayerIds(layers) {
  return (layers || []).filter(isGeoTransitLayer).map((layer) => layer.id);
}

export function touchesTransit(ids, geoIds) {
  const geo = new Set(geoIds);
  return (ids || []).some((id) => geo.has(id));
}

export function isPlanSourceError(event) {
  if (!event) return false;
  return event.sourceId === PLAN_GROUP || (!!event.source && event.source.id === PLAN_GROUP);
}
