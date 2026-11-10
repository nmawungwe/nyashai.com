// WebGL layer that redraws the pavilion artwork with per-pixel depth parallax.
// It sits over the <img>, which stays as the first paint and the fallback.

export interface SceneView {
  /** Camera offset as a fraction of the artwork size; near and far move apart. */
  shiftX: number;
  shiftY: number;
  /** Forward camera travel towards the focus point. */
  dolly: number;
  focusX: number;
  focusY: number;
  /** Seconds of running time, for the breeze. */
  time: number;
  /** 0..1 strength of the foliage sway. */
  breeze: number;
}

interface SceneConfig {
  /** Atlas baked by scripts/bake-depth.py: depth on top, foliage mask below. */
  depth: string;
  /** Depth that stays still (the worktable), so object links stay on target. */
  focal: number;
  focus: [number, number];
}

const MAX_PIXELS = 3_000_000;
const VERTEX = `
attribute vec2 aPosition;
varying vec2 vUv;
void main() {
  vUv = vec2(aPosition.x * 0.5 + 0.5, 0.5 - aPosition.y * 0.5);
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`;
const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec2 vUv;
uniform sampler2D uColor;
uniform sampler2D uAtlas;
uniform vec2 uShift;
uniform vec2 uFocus;
uniform float uDolly;
uniform float uFocal;
uniform float uTime;
uniform float uBreeze;
uniform float uAspect;
const int STEPS = 24;
const float SEAM = 0.002;

float depthAt(vec2 uv) {
  return texture2D(uAtlas, vec2(uv.x, clamp(uv.y, 0.0, 1.0) * (0.5 - SEAM))).r;
}
float foliageAt(vec2 uv) {
  return texture2D(uAtlas, vec2(uv.x, 0.5 + SEAM + clamp(uv.y, 0.0, 1.0) * (0.5 - SEAM))).r;
}

void main() {
  // Pin the borders so nothing is pulled in from outside the artwork.
  vec2 border = smoothstep(0.0, 0.07, vUv) * smoothstep(0.0, 0.07, 1.0 - vUv);
  vec2 ray = (uShift + (vUv - uFocus) * uDolly) * border.x * border.y;

  // Walk the depth layers from near to far; the first surface hit is visible.
  float layer = 1.0;
  float previousLayer = 1.0;
  vec2 uv = vUv - ray * (layer - uFocal);
  float depth = depthAt(uv);
  float previousDepth = depth;
  for (int i = 0; i < STEPS; i++) {
    if (depth >= layer) break;
    previousLayer = layer;
    previousDepth = depth;
    layer -= 1.0 / float(STEPS);
    uv = vUv - ray * (layer - uFocal);
    depth = depthAt(uv);
  }
  float before = previousLayer - previousDepth;
  float after = depth - layer;
  float hit = mix(previousLayer, layer, before / max(before + after, 0.00001));
  uv = vUv - ray * (hit - uFocal);

  // Leaves sway in slow gusts that travel across the garden.
  float gust = 0.55 + 0.45 * sin(uTime * 0.4 - uv.x * 5.0 + uv.y * 2.0);
  vec2 sway = vec2(
    sin(uTime * 1.5 + uv.y * 46.0 + uv.x * 19.0),
    sin(uTime * 1.2 + uv.x * 37.0)
  ) * vec2(0.0017 / uAspect, 0.0009);
  uv += sway * gust * foliageAt(uv) * uBreeze;

  gl_FragColor = vec4(texture2D(uColor, uv).rgb, 1.0);
}`;

function compile(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
}

export function createDepthLayer(canvas: HTMLCanvasElement, image: HTMLImageElement, onChange: () => void) {
  let scenes: Record<'landscape' | 'portrait', SceneConfig>;
  try {
    scenes = JSON.parse(canvas.dataset.scenes ?? '');
  } catch {
    return null;
  }
  const gl = canvas.getContext('webgl', {
    alpha: false, antialias: false, depth: false, stencil: false, powerPreference: 'low-power',
  });
  if (!gl) return null;

  const uniforms = new Map<string, WebGLUniformLocation | null>();
  let textures: (WebGLTexture | null)[] = [];
  let scene: SceneConfig | null = null;
  let aspect = 1;
  let quality = 1;
  let resized = true;
  let loads = 0;

  function setScene(next: SceneConfig | null) {
    if (scene === next) return;
    scene = next;
    onChange();
  }

  function setup() {
    const vertex = compile(gl!, gl!.VERTEX_SHADER, VERTEX);
    const fragment = compile(gl!, gl!.FRAGMENT_SHADER, FRAGMENT);
    const program = gl!.createProgram();
    if (!vertex || !fragment || !program) return false;
    gl!.attachShader(program, vertex);
    gl!.attachShader(program, fragment);
    gl!.linkProgram(program);
    if (!gl!.getProgramParameter(program, gl!.LINK_STATUS)) return false;
    gl!.useProgram(program);

    // One oversized triangle covers the canvas.
    gl!.bindBuffer(gl!.ARRAY_BUFFER, gl!.createBuffer());
    gl!.bufferData(gl!.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl!.STATIC_DRAW);
    const position = gl!.getAttribLocation(program, 'aPosition');
    gl!.enableVertexAttribArray(position);
    gl!.vertexAttribPointer(position, 2, gl!.FLOAT, false, 0, 0);

    for (const name of ['uColor', 'uAtlas', 'uShift', 'uFocus', 'uDolly', 'uFocal', 'uTime', 'uBreeze', 'uAspect']) {
      uniforms.set(name, gl!.getUniformLocation(program, name));
    }
    gl!.uniform1i(uniforms.get('uColor')!, 0);
    gl!.uniform1i(uniforms.get('uAtlas')!, 1);
    gl!.pixelStorei(gl!.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl!.NONE);
    textures = [0, 1].map((unit) => {
      const texture = gl!.createTexture();
      gl!.activeTexture(gl!.TEXTURE0 + unit);
      gl!.bindTexture(gl!.TEXTURE_2D, texture);
      // Clamped, unmipped sampling is required for non-power-of-two artwork.
      gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_WRAP_S, gl!.CLAMP_TO_EDGE);
      gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_WRAP_T, gl!.CLAMP_TO_EDGE);
      gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_MIN_FILTER, gl!.LINEAR);
      gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_MAG_FILTER, gl!.LINEAR);
      return texture;
    });
    return true;
  }

  function upload(unit: number, source: HTMLImageElement) {
    gl!.activeTexture(gl!.TEXTURE0 + unit);
    gl!.bindTexture(gl!.TEXTURE_2D, textures[unit]);
    gl!.texImage2D(gl!.TEXTURE_2D, 0, gl!.RGB, gl!.RGB, gl!.UNSIGNED_BYTE, source);
  }

  // The <picture> swaps artwork with the viewport shape; follow whichever is showing.
  async function load() {
    const ticket = ++loads;
    setScene(null);
    if (!image.complete || !image.naturalWidth || gl!.isContextLost()) return;
    const next = image.naturalWidth >= image.naturalHeight ? scenes.landscape : scenes.portrait;
    const atlas = new Image();
    atlas.src = next.depth;
    try {
      await atlas.decode();
      if (ticket !== loads || gl!.isContextLost()) return;
      upload(0, image);
      upload(1, atlas);
    } catch {
      return;
    }
    aspect = image.naturalWidth / image.naturalHeight;
    setScene(next);
  }

  function resize() {
    resized = false;
    const density = Math.min(window.devicePixelRatio || 1, 2) * quality;
    let width = canvas.clientWidth * density;
    let height = canvas.clientHeight * density;
    const excess = Math.sqrt((width * height) / MAX_PIXELS);
    if (excess > 1) {
      width /= excess;
      height /= excess;
    }
    canvas.width = Math.max(1, Math.round(width));
    canvas.height = Math.max(1, Math.round(height));
    gl!.viewport(0, 0, canvas.width, canvas.height);
  }

  if (!setup()) return null;
  new ResizeObserver(() => { resized = true; }).observe(canvas);
  image.addEventListener('load', () => void load());
  canvas.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    loads++;
    setScene(null);
  });
  canvas.addEventListener('webglcontextrestored', () => {
    if (setup()) void load();
  });
  void load();

  return {
    /** True once the artwork and its depth are on the GPU. */
    get ready() { return scene !== null; },
    /** Where the camera travels when no object link is visible. */
    get focus() { return scene?.focus ?? [0.6, 0.6]; },
    /** Lower the drawing resolution on devices that cannot keep up. */
    setQuality(scale: number) {
      quality = scale;
      resized = true;
    },
    draw(view: SceneView) {
      if (!scene) return;
      if (resized) resize();
      gl.uniform2f(uniforms.get('uShift')!, view.shiftX, view.shiftY);
      gl.uniform2f(uniforms.get('uFocus')!, view.focusX, view.focusY);
      gl.uniform1f(uniforms.get('uDolly')!, view.dolly);
      gl.uniform1f(uniforms.get('uFocal')!, scene.focal);
      gl.uniform1f(uniforms.get('uTime')!, view.time);
      gl.uniform1f(uniforms.get('uBreeze')!, view.breeze);
      gl.uniform1f(uniforms.get('uAspect')!, aspect);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
  };
}
