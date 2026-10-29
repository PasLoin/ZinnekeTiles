export const ROOFS_LAYER_ID = 'roofs-3d';
export const ROOFS_URL = './roofs.glb';
export const EARTH_RADIUS = 6371008.8;

const GLB_MAGIC = 0x46546c67;
const CHUNK_JSON = 0x4e4f534a;
const CHUNK_BIN = 0x004e4942;

const VERTEX_SHADER = `
attribute vec3 a_pos;
attribute vec4 a_color;
uniform mat4 u_matrix;
varying vec4 v_color;
void main() {
  v_color = a_color;
  gl_Position = u_matrix * vec4(a_pos, 1.0);
}`;

const FRAGMENT_SHADER = `
precision mediump float;
uniform float u_opacity;
varying vec4 v_color;
void main() {
  gl_FragColor = vec4(v_color.rgb * u_opacity, u_opacity);
}`;

const TYPED = {
  5121: Uint8Array,
  5123: Uint16Array,
  5125: Uint32Array,
  5126: Float32Array,
};

const SIZE = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };

export function eavesHeight(expr) {
  return ['case', ['has', 'roof_eaves'], ['to-number', ['get', 'roof_eaves'], 0], expr];
}

export function mercatorZScale(lat) {
  return 1 / (2 * Math.PI * EARTH_RADIUS * Math.cos((lat * Math.PI) / 180));
}

export function parseGlb(buffer) {
  const view = new DataView(buffer);
  if (buffer.byteLength < 20 || view.getUint32(0, true) !== GLB_MAGIC) {
    throw new Error('roofs.glb : en-tête glTF binaire invalide');
  }
  let offset = 12;
  let json = null;
  let bin = null;
  while (offset + 8 <= buffer.byteLength) {
    const length = view.getUint32(offset, true);
    const type = view.getUint32(offset + 4, true);
    const start = offset + 8;
    if (type === CHUNK_JSON) json = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, start, length)));
    else if (type === CHUNK_BIN) bin = { start, length };
    offset = start + length;
  }
  if (!json || !bin) throw new Error('roofs.glb : bloc JSON ou BIN manquant');

  const accessor = (index) => {
    const acc = json.accessors[index];
    const bv = json.bufferViews[acc.bufferView];
    const Type = TYPED[acc.componentType];
    const byteOffset = bin.start + (bv.byteOffset || 0) + (acc.byteOffset || 0);
    return new Type(buffer, byteOffset, acc.count * SIZE[acc.type]);
  };

  const extras = (json.asset && json.asset.extras) || {};
  const meshes = (json.nodes || [])
    .filter((node) => Number.isInteger(node.mesh))
    .flatMap((node) => json.meshes[node.mesh].primitives.map((prim) => ({
      translation: node.translation || [0, 0, 0],
      positions: accessor(prim.attributes.POSITION),
      colors: accessor(prim.attributes.COLOR_0),
      indices: accessor(prim.indices),
    })));
  return {
    mercator: extras.mercator || [0, 0],
    metersPerUnit: extras.metersPerUnit || 1,
    meshes,
  };
}

export function nodeMatrix(mercator, metersPerUnit, translation, zScale) {
  const k = 1 / metersPerUnit;
  return [
    k, 0, 0, 0,
    0, 0, zScale, 0,
    0, k, 0, 0,
    mercator[0] + translation[0] * k, mercator[1] + translation[2] * k, translation[1] * zScale, 1,
  ];
}

export function multiply(a, b) {
  const out = new Float64Array(16);
  for (let col = 0; col < 4; col++) {
    for (let row = 0; row < 4; row++) {
      let sum = 0;
      for (let i = 0; i < 4; i++) sum += a[i * 4 + row] * b[col * 4 + i];
      out[col * 4 + row] = sum;
    }
  }
  return out;
}

function mainMatrix(arg) {
  if (arg && arg.defaultProjectionData) return arg.defaultProjectionData.mainMatrix;
  return arg;
}

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader) || 'roofs : shader invalide');
  }
  return shader;
}

export function createRoofsLayer({
  id = ROOFS_LAYER_ID,
  url = ROOFS_URL,
  minzoom = 13,
  opacity = 0.75,
  fetchImpl = (...args) => fetch(...args),
  onLoad = () => {},
  onError = () => {},
} = {}) {
  let map = null;
  let program = null;
  let locations = null;
  let data = null;
  let buffers = [];
  let enabled = false;

  function upload(gl) {
    buffers = data.meshes.map((mesh) => {
      const position = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, position);
      gl.bufferData(gl.ARRAY_BUFFER, mesh.positions, gl.STATIC_DRAW);
      const color = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, color);
      gl.bufferData(gl.ARRAY_BUFFER, mesh.colors, gl.STATIC_DRAW);
      const index = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, index);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);
      const indexType = mesh.indices instanceof Uint32Array ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT;
      return { position, color, index, count: mesh.indices.length, indexType, translation: mesh.translation };
    });
    gl.bindBuffer(gl.ARRAY_BUFFER, null);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, null);
  }

  function drawAll(gl, matrix, zScale) {
    for (const mesh of buffers) {
      const m = multiply(matrix, nodeMatrix(data.mercator, data.metersPerUnit, mesh.translation, zScale));
      gl.uniformMatrix4fv(locations.matrix, false, new Float32Array(m));
      gl.bindBuffer(gl.ARRAY_BUFFER, mesh.position);
      gl.vertexAttribPointer(locations.pos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, mesh.color);
      gl.vertexAttribPointer(locations.color, 4, gl.UNSIGNED_BYTE, true, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.index);
      gl.drawElements(gl.TRIANGLES, mesh.count, mesh.indexType, 0);
    }
  }

  const layer = {
    id,
    type: 'custom',
    renderingMode: '3d',

    get loaded() {
      return buffers.length > 0;
    },

    setEnabled(value) {
      if (enabled === !!value) return;
      enabled = !!value;
      if (map) map.triggerRepaint();
    },

    onAdd(m, gl) {
      map = m;
      const vs = compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
      const fs = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
      program = gl.createProgram();
      gl.attachShader(program, vs);
      gl.attachShader(program, fs);
      gl.linkProgram(program);
      locations = {
        pos: gl.getAttribLocation(program, 'a_pos'),
        color: gl.getAttribLocation(program, 'a_color'),
        matrix: gl.getUniformLocation(program, 'u_matrix'),
        opacity: gl.getUniformLocation(program, 'u_opacity'),
      };
      fetchImpl(url)
        .then((response) => {
          if (!response.ok) throw new Error(`roofs.glb : HTTP ${response.status}`);
          return response.arrayBuffer();
        })
        .then((buffer) => {
          if (!map) return;
          data = parseGlb(buffer);
          upload(gl);
          map.triggerRepaint();
          onLoad(layer);
        })
        .catch((err) => {
          console.warn('Toits 3D indisponibles :', err);
          onError(err);
        });
    },

    onRemove(m, gl) {
      for (const mesh of buffers) {
        gl.deleteBuffer(mesh.position);
        gl.deleteBuffer(mesh.color);
        gl.deleteBuffer(mesh.index);
      }
      if (program) gl.deleteProgram(program);
      buffers = [];
      program = null;
      map = null;
    },

    render(gl, arg) {
      if (!enabled || !buffers.length || !program || map.getZoom() < minzoom) return;
      const matrix = mainMatrix(arg);
      const zScale = mercatorZScale(map.getCenter().lat);

      gl.useProgram(program);
      gl.enableVertexAttribArray(locations.pos);
      gl.enableVertexAttribArray(locations.color);
      gl.disable(gl.CULL_FACE);

      gl.colorMask(false, false, false, false);
      gl.depthMask(true);
      gl.uniform1f(locations.opacity, opacity);
      drawAll(gl, matrix, zScale);

      gl.colorMask(true, true, true, true);
      gl.depthMask(false);
      gl.depthFunc(gl.EQUAL);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      drawAll(gl, matrix, zScale);

      gl.depthMask(true);
      gl.depthFunc(gl.LEQUAL);
      gl.disableVertexAttribArray(locations.pos);
      gl.disableVertexAttribArray(locations.color);
      gl.bindBuffer(gl.ARRAY_BUFFER, null);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, null);
    },
  };
  return layer;
}
