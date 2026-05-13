// Custom MapLibre WebGL layer: Gaussian-blurred directional drop shadow
// under the currently-selected polygon feature.
//
// Pipeline (per frame, only while opacity > 0 OR animating):
//   prerender:
//     1. Bind FBO A. Clear. Use mask program. Draw selected polygon triangles
//        in Mercator coords transformed by MapLibre's u_matrix → silhouette.
//     2. Bind FBO B. Clear. Blur program, horizontal direction. Sample FBO A.
//     3. Bind FBO A. Clear. Blur program, vertical direction. Sample FBO B.
//        FBO A now holds the soft shadow mask.
//   render:
//     - Use composite program. Sample FBO A with screen-space offset.
//        Premultiplied-alpha blend onto MapLibre's main framebuffer.
//
// Geometry: GeoJSON polygon rings → Mercator [0,1] coords → earcut → VBO+IBO.
// Cached per `${level}:${id}` to avoid re-triangulating Hawaii's coastlines.

import maplibregl from 'maplibre-gl';
import earcut from 'earcut';
import { getFeatureById } from './layerManager.js';

export const SHADOW_LAYER_ID = 'selection-shadow';

// Visual tuning knobs.
const BLUR_RADIUS_PX = 12;        // Gaussian radius for the two-pass blur.
const OFFSET_PX = [6, 8];         // Shadow displacement (x right, y down).
const SHADOW_RGB = [0.0, 0.0, 0.0]; // Premultiplied with alpha at composite.
const SHADOW_MAX_ALPHA = 0.55;    // Peak opacity at fully selected.
const FADE_MS = 300;
const GEOM_CACHE_MAX = 32;        // LRU cap for triangulated buffers.

// ─── Shader sources ────────────────────────────────────────────────────────

// Mask: draw selected polygon as solid alpha=1 into an offscreen FBO.
const MASK_VS = `
  attribute vec2 a_pos;
  uniform mat4 u_matrix;
  void main() {
    gl_Position = u_matrix * vec4(a_pos, 0.0, 1.0);
  }
`;
const MASK_FS = `
  precision mediump float;
  void main() {
    gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
  }
`;

// Fullscreen quad vertex shader (used for blur + composite passes).
const QUAD_VS = `
  attribute vec2 a_quad;       // [-1,1] clip-space positions.
  varying vec2 v_uv;
  void main() {
    v_uv = a_quad * 0.5 + 0.5;
    gl_Position = vec4(a_quad, 0.0, 1.0);
  }
`;

// Separable Gaussian. 9-tap kernel collapsed into 5 linear-sampled taps
// (Rastergrid technique). u_direction is (1/W, 0) for the horizontal pass
// and (0, 1/H) for the vertical pass — encodes step size in UV units.
// Hardcoded sigma ≈ BLUR_RADIUS_PX/2; offsets/weights computed at module
// load so the shader stays a plain string.
const BLUR_FS = (() => {
  // Linear-sampled 5-tap weights for a 9-tap Gaussian. Standard sigma=2 kernel
  // collapsed via the linear-sampling trick: pairs of texels sampled at a
  // weighted midpoint.
  // Source: https://www.rastergrid.com/blog/2010/09/efficient-gaussian-blur-with-linear-sampling/
  return `
    precision mediump float;
    varying vec2 v_uv;
    uniform sampler2D u_tex;
    uniform vec2 u_direction;
    void main() {
      vec4 sum = texture2D(u_tex, v_uv) * 0.2270270270;
      sum += texture2D(u_tex, v_uv + u_direction * 1.3846153846) * 0.3162162162;
      sum += texture2D(u_tex, v_uv - u_direction * 1.3846153846) * 0.3162162162;
      sum += texture2D(u_tex, v_uv + u_direction * 3.2307692308) * 0.0702702703;
      sum += texture2D(u_tex, v_uv - u_direction * 3.2307692308) * 0.0702702703;
      gl_FragColor = sum;
    }
  `;
})();

// Composite: sample the blurred shadow texture at (frag - offset) and emit
// SHADOW_RGB * alpha with premultiplied blending. u_offset_uv is the offset
// expressed in texture-UV units (offsetPx / FBOsize).
const COMPOSITE_FS = `
  precision mediump float;
  varying vec2 v_uv;
  uniform sampler2D u_tex;
  uniform vec2 u_offset_uv;
  uniform vec3 u_shadow_color;
  uniform float u_opacity;
  void main() {
    vec2 src = v_uv - u_offset_uv;
    // Guard against sampling outside [0,1] — clamp to a fully transparent edge.
    if (src.x < 0.0 || src.x > 1.0 || src.y < 0.0 || src.y > 1.0) {
      gl_FragColor = vec4(0.0);
      return;
    }
    float a = texture2D(u_tex, src).a * u_opacity;
    gl_FragColor = vec4(u_shadow_color * a, a); // premultiplied
  }
`;

// ─── GL helpers ────────────────────────────────────────────────────────────

function compile(gl, type, src) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(sh);
    gl.deleteShader(sh);
    throw new Error('Shader compile failed: ' + log);
  }
  return sh;
}

function link(gl, vs, fs) {
  const p = gl.createProgram();
  gl.attachShader(p, vs);
  gl.attachShader(p, fs);
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(p);
    gl.deleteProgram(p);
    throw new Error('Program link failed: ' + log);
  }
  return p;
}

function makeProgram(gl, vsSrc, fsSrc) {
  const vs = compile(gl, gl.VERTEX_SHADER, vsSrc);
  const fs = compile(gl, gl.FRAGMENT_SHADER, fsSrc);
  const p = link(gl, vs, fs);
  // Shaders can be detached/deleted after link.
  gl.detachShader(p, vs);
  gl.detachShader(p, fs);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  return p;
}

function makeFBO(gl, w, h) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  return { fbo, tex, width: w, height: h };
}

function destroyFBO(gl, target) {
  if (!target) return;
  gl.deleteFramebuffer(target.fbo);
  gl.deleteTexture(target.tex);
}

// ─── Geometry: GeoJSON → Mercator-triangulated VBO+IBO ─────────────────────

// Flatten one polygon (outer ring + holes) into earcut input.
// Each ring is an array of [lng, lat]. Returns { flatXY, holes }.
function flattenPolygon(rings) {
  const flat = [];
  const holes = [];
  for (let r = 0; r < rings.length; r++) {
    if (r > 0) holes.push(flat.length / 2);
    const ring = rings[r];
    for (const [lng, lat] of ring) {
      const mc = maplibregl.MercatorCoordinate.fromLngLat({ lng, lat });
      flat.push(mc.x, mc.y);
    }
  }
  return { flat, holes };
}

// Build a single VBO+IBO from a Polygon or MultiPolygon feature.
// MultiPolygon: concatenate each polygon's triangulation with index offsets.
function buildGeometry(gl, feature) {
  const geom = feature.geometry;
  if (!geom) return null;

  const polygons = geom.type === 'MultiPolygon'
    ? geom.coordinates
    : geom.type === 'Polygon' ? [geom.coordinates] : null;
  if (!polygons || polygons.length === 0) return null;

  const allPositions = [];
  const allIndices = [];
  let vertexOffset = 0;

  for (const rings of polygons) {
    const { flat, holes } = flattenPolygon(rings);
    if (flat.length < 6) continue; // need at least 3 verts
    const idx = earcut(flat, holes, 2);
    if (idx.length === 0) continue;
    allPositions.push(...flat);
    for (const i of idx) allIndices.push(i + vertexOffset);
    vertexOffset += flat.length / 2;
  }

  if (allIndices.length === 0) return null;

  const posArr = new Float32Array(allPositions);
  const idxArr = allIndices.length > 65535
    ? new Uint32Array(allIndices)
    : new Uint16Array(allIndices);

  const vbo = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
  gl.bufferData(gl.ARRAY_BUFFER, posArr, gl.STATIC_DRAW);

  const ibo = gl.createBuffer();
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idxArr, gl.STATIC_DRAW);

  return {
    vbo,
    ibo,
    indexCount: idxArr.length,
    indexType: idxArr instanceof Uint32Array ? 0x1405 /* UNSIGNED_INT */ : gl.UNSIGNED_SHORT,
  };
}

function destroyGeometry(gl, g) {
  if (!g) return;
  gl.deleteBuffer(g.vbo);
  gl.deleteBuffer(g.ibo);
}

// ─── The custom layer ──────────────────────────────────────────────────────

class ShadowLayer {
  constructor() {
    this.id = SHADOW_LAYER_ID;
    this.type = 'custom';
    this.renderingMode = '2d';
    this.map = null;
    this.gl = null;
    // Programs + attribute/uniform locations.
    this.maskProgram = null;
    this.maskAttribPos = -1;
    this.maskUniMatrix = null;
    this.blurProgram = null;
    this.blurAttribQuad = -1;
    this.blurUniTex = null;
    this.blurUniDir = null;
    this.compProgram = null;
    this.compAttribQuad = -1;
    this.compUniTex = null;
    this.compUniOffset = null;
    this.compUniColor = null;
    this.compUniOpacity = null;
    // Fullscreen quad VBO.
    this.quadVBO = null;
    // FBOs (ping-pong).
    this.fboA = null;
    this.fboB = null;
    this.fboWidth = 0;
    this.fboHeight = 0;
    // Selection state.
    this.currentLevel = null;
    this.currentId = null;
    this.currentGeom = null;     // active GPU geometry handle
    this.geomCache = new Map();  // `${level}:${id}` → { vbo, ibo, ... }
    // Animation state.
    this.opacity = 0;
    this.targetOpacity = 0;
    this.lastTs = null;
    this._rafId = null;          // external rAF loop id (drives fade animation)
    // Bound listeners (for clean removal).
    this._onResize = null;
    this._onContextLost = null;
    this._onContextRestored = null;
    // Uint32 element index extension flag.
    this._uint32IndexEnabled = false;
    // Element index extension's UNSIGNED_INT constant (0x1405).
  }

  onAdd(map, gl) {
    this.map = map;
    this.gl = gl;

    // Enable Uint32 element indices (universally supported on real hardware).
    this._uint32IndexEnabled = !!gl.getExtension('OES_element_index_uint');

    // Build programs.
    this.maskProgram = makeProgram(gl, MASK_VS, MASK_FS);
    this.maskAttribPos = gl.getAttribLocation(this.maskProgram, 'a_pos');
    this.maskUniMatrix = gl.getUniformLocation(this.maskProgram, 'u_matrix');

    this.blurProgram = makeProgram(gl, QUAD_VS, BLUR_FS);
    this.blurAttribQuad = gl.getAttribLocation(this.blurProgram, 'a_quad');
    this.blurUniTex = gl.getUniformLocation(this.blurProgram, 'u_tex');
    this.blurUniDir = gl.getUniformLocation(this.blurProgram, 'u_direction');

    this.compProgram = makeProgram(gl, QUAD_VS, COMPOSITE_FS);
    this.compAttribQuad = gl.getAttribLocation(this.compProgram, 'a_quad');
    this.compUniTex = gl.getUniformLocation(this.compProgram, 'u_tex');
    this.compUniOffset = gl.getUniformLocation(this.compProgram, 'u_offset_uv');
    this.compUniColor = gl.getUniformLocation(this.compProgram, 'u_shadow_color');
    this.compUniOpacity = gl.getUniformLocation(this.compProgram, 'u_opacity');

    // Fullscreen triangle covering [-1,1]² (overdraws by 1 on each axis but
    // avoids the gap-at-pixel-center issue of a two-triangle quad).
    this.quadVBO = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadVBO);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1,  3, -1,  -1, 3,
    ]), gl.STATIC_DRAW);

    // FBOs sized to the drawing buffer (handles DPR).
    this._ensureFBOs();

    // Resize: recreate FBOs.
    this._onResize = () => this._ensureFBOs();
    this.map.on('resize', this._onResize);

    // Context loss: invalidate everything; the map will re-init on restore.
    this._onContextLost = (e) => { e.preventDefault(); };
    this._onContextRestored = () => { /* MapLibre handles re-add of layers */ };
    const canvas = this.map.getCanvas();
    canvas.addEventListener('webglcontextlost', this._onContextLost, false);
    canvas.addEventListener('webglcontextrestored', this._onContextRestored, false);
  }

  onRemove(map, gl) {
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
    if (this._onResize) map.off('resize', this._onResize);
    const canvas = map.getCanvas();
    if (this._onContextLost) canvas.removeEventListener('webglcontextlost', this._onContextLost);
    if (this._onContextRestored) canvas.removeEventListener('webglcontextrestored', this._onContextRestored);

    if (this.maskProgram) gl.deleteProgram(this.maskProgram);
    if (this.blurProgram) gl.deleteProgram(this.blurProgram);
    if (this.compProgram) gl.deleteProgram(this.compProgram);
    if (this.quadVBO) gl.deleteBuffer(this.quadVBO);
    destroyFBO(gl, this.fboA);
    destroyFBO(gl, this.fboB);
    for (const g of this.geomCache.values()) destroyGeometry(gl, g);
    this.geomCache.clear();
  }

  _ensureFBOs() {
    const gl = this.gl;
    if (!gl) return;
    const w = gl.drawingBufferWidth;
    const h = gl.drawingBufferHeight;
    if (w === this.fboWidth && h === this.fboHeight && this.fboA && this.fboB) return;
    destroyFBO(gl, this.fboA);
    destroyFBO(gl, this.fboB);
    this.fboA = makeFBO(gl, w, h);
    this.fboB = makeFBO(gl, w, h);
    this.fboWidth = w;
    this.fboHeight = h;
  }

  // Public: set or clear the selected feature. `feature` may be null to clear.
  setFeature(level, feature) {
    if (!feature) {
      // Fade out; geometry stays bound until opacity hits 0 so the fade
      // animation has something to draw.
      this.targetOpacity = 0;
      this._startAnimationPump();
      return;
    }
    const id = String(feature.id ?? feature.properties?.GEOID ?? '');
    if (!id) return;
    const key = `${level}:${id}`;

    let g = this.geomCache.get(key);
    if (!g) {
      if (!this.gl) {
        // Layer not yet added; defer.
        this.currentLevel = level;
        this.currentId = id;
        this._pendingFeature = feature;
        this.targetOpacity = 1;
        return;
      }
      g = buildGeometry(this.gl, feature);
      if (!g) return;
      // Simple LRU: insertion order. If at cap, drop oldest entry.
      if (this.geomCache.size >= GEOM_CACHE_MAX) {
        const firstKey = this.geomCache.keys().next().value;
        const firstGeom = this.geomCache.get(firstKey);
        this.geomCache.delete(firstKey);
        destroyGeometry(this.gl, firstGeom);
      }
      this.geomCache.set(key, g);
    } else {
      // Touch for LRU recency.
      this.geomCache.delete(key);
      this.geomCache.set(key, g);
    }

    this.currentLevel = level;
    this.currentId = id;
    this.currentGeom = g;
    this.targetOpacity = 1;
    this._startAnimationPump();
  }

  // Drive the fade animation from an external requestAnimationFrame loop.
  // `map.triggerRepaint()` called from inside render() doesn't reliably
  // schedule subsequent frames — MapLibre coalesces repaints during render.
  // By pumping repaint from rAF outside, we get a true 60fps fade.
  _startAnimationPump() {
    if (this._rafId || !this.map) return;
    const tick = () => {
      this._rafId = null;
      if (this.opacity === this.targetOpacity) return;
      this.map.triggerRepaint();
      this._rafId = requestAnimationFrame(tick);
    };
    this._rafId = requestAnimationFrame(tick);
  }

  // Pump fade animation. Returns the eased opacity to use this frame.
  _stepAnimation() {
    if (this.opacity === this.targetOpacity) {
      this.lastTs = null;
      return this.opacity;
    }
    const now = performance.now();
    const dt = this.lastTs ? Math.min(now - this.lastTs, 50) : 16;
    this.lastTs = now;
    const step = dt / FADE_MS;
    const dir = Math.sign(this.targetOpacity - this.opacity);
    this.opacity = Math.max(0, Math.min(1, this.opacity + dir * step));
    if (this.opacity !== this.targetOpacity) this.map.triggerRepaint();
    else this.lastTs = null;
    // Ease-out cubic for natural feel.
    return 1 - Math.pow(1 - this.opacity, 3);
  }

  prerender(gl, _matrix) {
    // If we have a pending feature from before onAdd, materialize it now.
    if (this._pendingFeature) {
      const pf = this._pendingFeature;
      this._pendingFeature = null;
      this.setFeature(this.currentLevel, pf);
    }
    if (this.targetOpacity === 0 && this.opacity === 0) return; // fully idle
    if (!this.currentGeom || !this.fboA || !this.fboB) return;

    this._ensureFBOs(); // safety; resize listener should already handle this
    const w = this.fboWidth, h = this.fboHeight;

    // ─── Pass 1: mask into FBO A ──
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fboA.fbo);
    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.disable(gl.BLEND); // overwrite, not blend

    gl.useProgram(this.maskProgram);
    // MapLibre's projection matrix is on the active layer's render args, but
    // the docs note `_matrix` here may be undefined in prerender. Use the
    // up-to-date matrix that MapLibre stores on the transform via its public
    // getMatrixForModel(); we can also rely on the render args matrix in
    // `render()` since FBOs persist. Solution: do mask in `render()`? No —
    // we still need the matrix. Use map.transform.projMatrix as the
    // proj-from-mercator matrix (this is what custom-layer examples use).
    const projMatrix = this._getProjMatrix();
    gl.uniformMatrix4fv(this.maskUniMatrix, false, projMatrix);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.currentGeom.vbo);
    gl.enableVertexAttribArray(this.maskAttribPos);
    gl.vertexAttribPointer(this.maskAttribPos, 2, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.currentGeom.ibo);
    gl.drawElements(gl.TRIANGLES, this.currentGeom.indexCount, this.currentGeom.indexType, 0);
    gl.disableVertexAttribArray(this.maskAttribPos);

    // ─── Pass 2: horizontal blur — sample A, write B ──
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fboB.fbo);
    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(this.blurProgram);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.fboA.tex);
    gl.uniform1i(this.blurUniTex, 0);
    gl.uniform2f(this.blurUniDir, (BLUR_RADIUS_PX / 8) / w, 0); // scale step to radius
    this._drawQuad(this.blurAttribQuad);

    // ─── Pass 3: vertical blur — sample B, write A ──
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fboA.fbo);
    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.bindTexture(gl.TEXTURE_2D, this.fboB.tex);
    gl.uniform1i(this.blurUniTex, 0);
    gl.uniform2f(this.blurUniDir, 0, (BLUR_RADIUS_PX / 8) / h);
    this._drawQuad(this.blurAttribQuad);

    // Hand control back to MapLibre. It rebinds its own framebuffer for
    // `render()` automatically.
  }

  render(gl, _matrix) {
    // Animate every frame (cheap; only repaints itself when changing).
    const eased = this._stepAnimation();
    if (this.opacity === 0 && this.targetOpacity === 0) return;
    if (!this.currentGeom || !this.fboA) return;

    const finalOpacity = eased * SHADOW_MAX_ALPHA;
    if (finalOpacity <= 0.001) return;

    // Composite blurred shadow with screen-space directional offset.
    // MapLibre has rebound the main framebuffer + viewport for us.
    gl.useProgram(this.compProgram);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.fboA.tex);
    gl.uniform1i(this.compUniTex, 0);
    // Convert px offset → UV offset using FBO dimensions (FBO and main
    // framebuffer share px size).
    gl.uniform2f(this.compUniOffset, OFFSET_PX[0] / this.fboWidth, -OFFSET_PX[1] / this.fboHeight);
    gl.uniform3f(this.compUniColor, SHADOW_RGB[0], SHADOW_RGB[1], SHADOW_RGB[2]);
    gl.uniform1f(this.compUniOpacity, finalOpacity);

    // Premultiplied alpha blend — match MapLibre's default state.
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    this._drawQuad(this.compAttribQuad);
  }

  _drawQuad(attribLoc) {
    const gl = this.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadVBO);
    gl.enableVertexAttribArray(attribLoc);
    gl.vertexAttribPointer(attribLoc, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.disableVertexAttribArray(attribLoc);
  }

  // Mercator-to-clip projection matrix used by the mask pass.
  // MapLibre exposes this on transform.projMatrix; if missing on a given
  // version, fall back to building it from the canonical Mercator transform.
  _getProjMatrix() {
    const t = this.map.transform;
    return t.projMatrix || t.mercatorMatrix || t.matrix;
  }
}

// ─── Module-level singleton + public API ───────────────────────────────────

let _instance = null;

export function registerShadowLayer(map) {
  if (!map) return;
  if (_instance && map.getLayer(SHADOW_LAYER_ID)) return _instance;
  if (!_instance) _instance = new ShadowLayer();
  if (!map.getLayer(SHADOW_LAYER_ID)) {
    map.addLayer(_instance);
  }
  return _instance;
}

export function setShadowFeature(level, feature) {
  if (!_instance) return;
  // Look up canonical geometry from layerManager's cache when given an id-only
  // reference; the popup hands us a click feature whose geometry may be
  // tile-clipped at very high zoom, so prefer the original GeoJSON.
  if (feature && (feature.id != null || feature.properties)) {
    const id = feature.id ?? feature.properties?.GEOID;
    const canonical = id != null ? getFeatureById(level, id) : null;
    _instance.setFeature(level, canonical || feature);
    return;
  }
  _instance.setFeature(level, null);
}
