import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  ROOFS_LAYER_ID, eavesHeight, mercatorZScale, parseGlb, nodeMatrix, multiply, createRoofsLayer,
} from '../../www/roofs.js';

function buildGlb({ extras = {}, translation = [10, 0, -20] } = {}) {
  const positions = new Float32Array([0, 0, 0, 1, 0, 0, 0, 2, 1]);
  const colors = new Uint8Array([255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255]);
  const indices = new Uint16Array([0, 1, 2, 0]);
  const bin = new Uint8Array(positions.byteLength + colors.byteLength + indices.byteLength);
  bin.set(new Uint8Array(positions.buffer), 0);
  bin.set(colors, 36);
  bin.set(new Uint8Array(indices.buffer), 48);
  const doc = {
    asset: { version: '2.0', extras: { mercator: [0.5, 0.33], metersPerUnit: 25000000, ...extras } },
    nodes: [{ mesh: 0, translation }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0, COLOR_0: 1 }, indices: 2 }] }],
    accessors: [
      { bufferView: 0, componentType: 5126, count: 3, type: 'VEC3' },
      { bufferView: 1, componentType: 5121, normalized: true, count: 3, type: 'VEC4' },
      { bufferView: 2, componentType: 5123, count: 3, type: 'SCALAR' },
    ],
    bufferViews: [
      { buffer: 0, byteOffset: 0, byteLength: 36 },
      { buffer: 0, byteOffset: 36, byteLength: 12 },
      { buffer: 0, byteOffset: 48, byteLength: 6 },
    ],
    buffers: [{ byteLength: bin.byteLength }],
  };
  let json = new TextEncoder().encode(JSON.stringify(doc));
  const pad = (4 - (json.length % 4)) % 4;
  json = new Uint8Array([...json, ...new Array(pad).fill(32)]);
  const total = 12 + 8 + json.length + 8 + bin.length;
  const out = new ArrayBuffer(total);
  const view = new DataView(out);
  view.setUint32(0, 0x46546c67, true);
  view.setUint32(4, 2, true);
  view.setUint32(8, total, true);
  view.setUint32(12, json.length, true);
  view.setUint32(16, 0x4e4f534a, true);
  new Uint8Array(out, 20, json.length).set(json);
  view.setUint32(20 + json.length, bin.length, true);
  view.setUint32(24 + json.length, 0x004e4942, true);
  new Uint8Array(out, 28 + json.length, bin.length).set(bin);
  return out;
}

function transform(m, p) {
  const out = [0, 0, 0, 0];
  for (let row = 0; row < 4; row++) {
    out[row] = m[row] * p[0] + m[4 + row] * p[1] + m[8 + row] * p[2] + m[12 + row] * p[3];
  }
  return out;
}

function mockGl() {
  const calls = [];
  const gl = new Proxy({}, {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (typeof prop === 'string' && /^[A-Z_0-9]+$/.test(prop)) return prop;
      return (...args) => {
        calls.push([prop, ...args]);
        if (prop === 'getShaderParameter') return true;
        if (prop === 'getAttribLocation') return args[1] === 'a_pos' ? 0 : 1;
        if (prop.startsWith('create')) return { kind: prop };
        return undefined;
      };
    },
  });
  return { gl, calls };
}

function mockMap(zoom = 17) {
  return { getZoom: () => zoom, getCenter: () => ({ lat: 50.85 }), triggerRepaint: vi.fn() };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];

describe('eavesHeight', () => {
  it('coupe à roof_eaves quand la propriété existe, sinon garde l’expression', () => {
    const original = ['get', 'height'];
    expect(eavesHeight(original)).toEqual(
      ['case', ['has', 'roof_eaves'], ['to-number', ['get', 'roof_eaves'], 0], original],
    );
  });
});

describe('mercatorZScale', () => {
  it('correspond à l’inverse de la circonférence à la latitude', () => {
    expect(mercatorZScale(0)).toBeCloseTo(1 / (2 * Math.PI * 6371008.8), 15);
    expect(mercatorZScale(60) / mercatorZScale(0)).toBeCloseTo(2, 10);
  });
});

describe('parseGlb', () => {
  it('lit les nœuds, attributs et indices', () => {
    const data = parseGlb(buildGlb());
    expect(data.mercator).toEqual([0.5, 0.33]);
    expect(data.metersPerUnit).toBe(25000000);
    expect(data.meshes).toHaveLength(1);
    const [mesh] = data.meshes;
    expect(mesh.translation).toEqual([10, 0, -20]);
    expect(Array.from(mesh.positions)).toEqual([0, 0, 0, 1, 0, 0, 0, 2, 1]);
    expect(mesh.colors).toBeInstanceOf(Uint8Array);
    expect(Array.from(mesh.indices)).toEqual([0, 1, 2]);
  });

  it('refuse un fichier qui n’est pas un glb', () => {
    expect(() => parseGlb(new ArrayBuffer(32))).toThrow(/en-tête/);
  });

  it('lit le roofs.glb publié', () => {
    const file = path.resolve(__dirname, '../../www/roofs.glb');
    if (!fs.existsSync(file)) return;
    const bytes = fs.readFileSync(file);
    const data = parseGlb(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
    expect(data.meshes.length).toBeGreaterThan(0);
    for (const mesh of data.meshes) {
      expect(mesh.positions.length % 3).toBe(0);
      expect(mesh.colors.length / 4).toBe(mesh.positions.length / 3);
      expect(Math.max(...mesh.indices)).toBeLessThan(mesh.positions.length / 3);
    }
  });
});

describe('nodeMatrix / multiply', () => {
  it('place un sommet local en coordonnées Mercator', () => {
    const m = nodeMatrix([0.5, 0.3], 1000, [100, 0, -200], 0.001);
    const [x, y, z, w] = transform(m, [50, 7, 30, 1]);
    expect(x).toBeCloseTo(0.5 + 0.15, 12);
    expect(y).toBeCloseTo(0.3 - 0.17, 12);
    expect(z).toBeCloseTo(0.007, 12);
    expect(w).toBe(1);
  });

  it('multiplie en colonne majeure', () => {
    const a = nodeMatrix([1, 2], 10, [0, 0, 0], 3);
    expect(Array.from(multiply(identity, a))).toEqual(a);
    const scale = [2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1];
    const p = transform(multiply(scale, a), [10, 1, 20, 1]);
    expect(p).toEqual(transform(scale, transform(a, [10, 1, 20, 1])));
  });
});

describe('createRoofsLayer', () => {
  it('est une couche custom 3D', () => {
    const layer = createRoofsLayer({ fetchImpl: vi.fn() });
    expect(layer.id).toBe(ROOFS_LAYER_ID);
    expect(layer.type).toBe('custom');
    expect(layer.renderingMode).toBe('3d');
    expect(layer.loaded).toBe(false);
  });

  it('charge le glb, prévient onLoad et dessine en deux passes', async () => {
    const onLoad = vi.fn();
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => buildGlb() });
    const layer = createRoofsLayer({ url: 'x.glb', fetchImpl, onLoad });
    const { gl, calls } = mockGl();
    const map = mockMap();
    layer.onAdd(map, gl);
    await flush();
    expect(fetchImpl).toHaveBeenCalledWith('x.glb');
    expect(onLoad).toHaveBeenCalledWith(layer);
    expect(layer.loaded).toBe(true);

    layer.render(gl, identity);
    expect(calls.filter(c => c[0] === 'drawElements')).toHaveLength(0);

    layer.setEnabled(true);
    expect(map.triggerRepaint).toHaveBeenCalled();
    layer.render(gl, identity);
    const draws = calls.filter(c => c[0] === 'drawElements');
    expect(draws).toHaveLength(2);
    expect(draws[0].slice(1)).toEqual(['TRIANGLES', 3, 'UNSIGNED_SHORT', 0]);
    expect(calls.some(c => c[0] === 'depthFunc' && c[1] === 'EQUAL')).toBe(true);
    expect(calls.at(-1)[0]).toBe('bindBuffer');
  });

  it('accepte la signature MapLibre 5 (defaultProjectionData)', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => buildGlb() });
    const layer = createRoofsLayer({ fetchImpl });
    const { gl, calls } = mockGl();
    layer.onAdd(mockMap(), gl);
    await flush();
    layer.setEnabled(true);
    layer.render(gl, { defaultProjectionData: { mainMatrix: identity } });
    expect(calls.filter(c => c[0] === 'drawElements')).toHaveLength(2);
  });

  it('ne dessine rien sous le zoom minimal', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => buildGlb() });
    const layer = createRoofsLayer({ fetchImpl, minzoom: 15 });
    const { gl, calls } = mockGl();
    layer.onAdd(mockMap(14), gl);
    await flush();
    layer.setEnabled(true);
    layer.render(gl, identity);
    expect(calls.filter(c => c[0] === 'drawElements')).toHaveLength(0);
  });

  it('appelle onError si le fichier est absent', async () => {
    const onError = vi.fn();
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    const layer = createRoofsLayer({ fetchImpl, onError });
    layer.onAdd(mockMap(), mockGl().gl);
    await flush();
    expect(onError).toHaveBeenCalled();
    expect(layer.loaded).toBe(false);
    warn.mockRestore();
  });

  it('libère les ressources GL à la suppression', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => buildGlb() });
    const layer = createRoofsLayer({ fetchImpl });
    const { gl, calls } = mockGl();
    layer.onAdd(mockMap(), gl);
    await flush();
    layer.onRemove(mockMap(), gl);
    expect(calls.filter(c => c[0] === 'deleteBuffer')).toHaveLength(3);
    expect(calls.some(c => c[0] === 'deleteProgram')).toBe(true);
    expect(layer.loaded).toBe(false);
  });
});
