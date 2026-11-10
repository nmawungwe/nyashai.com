import { Color, EquirectangularReflectionMapping, Fog, Material, Mesh, MeshBasicMaterial, NoToneMapping, Object3D, PerspectiveCamera, Quaternion, SRGBColorSpace, Scene, TextureLoader, Vector3, WebGLRenderer } from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import type { View } from './rig';

export { createRig } from './rig';
export { createLabels } from './labels';

interface CameraData { position: number[]; quaternion: number[]; yfov: number; aspect: number }
interface SceneData { cameras: Record<string, CameraData>; anchors: Record<string, number[]>; fog: string }

/**
 * Leaf-card textures store per-leaf brightness around 0.8 (display); the lit
 * colour lives in the vertex colours. This restores the mean to 1.0 (linear).
 */
const LEAF_GAIN = 1 / Math.pow(0.8, 2.2);
/** Alpha below this is cut from leaf cards. */
const LEAF_CUTOFF = 0.16;
/** Screens are emissive in the stills; through the view transform they read a touch below white. */
const SCREEN_LEVEL = 0.9;

/**
 * Loads the baked pavilion. Everything is unlit (KHR_materials_unlit): the GLB's
 * textures and vertex colours are already display-referred, so the renderer uses
 * sRGB output and no tone mapping.
 */
export async function loadScene(canvas: HTMLCanvasElement, base: string) {
  const renderer = new WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = NoToneMapping;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const [gltf, sky, data] = await Promise.all([
    loader.loadAsync(`${base}pavilion.glb`),
    new TextureLoader().loadAsync(`${base}sky.webp`),
    fetch(`${base}cameras.json`).then((r) => {
      if (!r.ok) throw new Error(`cameras.json ${r.status}`);
      return r.json() as Promise<SceneData>;
    }),
  ]);

  const scene = new Scene();
  sky.mapping = EquirectangularReflectionMapping;
  sky.colorSpace = SRGBColorSpace;
  scene.background = sky;
  // Distance haze in the baked haze colour; the bake already carries most of it,
  // so this only softens the far ridges a little further.
  scene.fog = new Fog(new Color(data.fog), 400, 4200);
  scene.add(gltf.scene);

  const breeze = { uTime: { value: 0 }, uBreeze: { value: 0 } };
  gltf.scene.traverse((obj: Object3D) => {
    const mesh = obj as Mesh;
    if (!mesh.isMesh) return;
    mesh.frustumCulled = true;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials as MeshBasicMaterial[]) {
      if (material.name.startsWith('leafcard')) {
        material.color.setScalar(LEAF_GAIN);
        // Cut-out leaves shimmer and speckle when each pixel is simply kept or
        // dropped; alpha-to-coverage lets multisampling blend their edges.
        material.alphaToCoverage = true;
        // Distant leaves average towards transparent in the smaller mip levels;
        // a low cut-off keeps the canopy full instead of thinning it out.
        material.alphaTest = LEAF_CUTOFF;
        if (material.map) material.map.anisotropy = renderer.capabilities.getMaxAnisotropy();
      }
      if (material.name.endsWith('screen_unlit')) material.color.setScalar(SCREEN_LEVEL);
      if (mesh.geometry.getAttribute('_sway')) addBreeze(material, breeze);
    }
  });

  const views = new Map<string, View>();
  for (const [name, cam] of Object.entries(data.cameras)) {
    views.set(name, {
      position: new Vector3().fromArray(cam.position),
      quaternion: new Quaternion().fromArray(cam.quaternion),
      yfov: cam.yfov,
      aspect: cam.aspect,
    });
  }
  const anchors = new Map<string, Vector3>();
  for (const [name, pos] of Object.entries(data.anchors)) {
    anchors.set(name.replace(/^anchor_/, ''), new Vector3().fromArray(pos));
  }
  const camera = new PerspectiveCamera(50, 1, 0.05, 6000);

  return {
    renderer,
    scene,
    camera,
    views,
    anchors,
    breeze,
    dispose() {
      scene.traverse((obj: Object3D) => {
        const mesh = obj as Mesh;
        if (!mesh.isMesh) return;
        mesh.geometry.dispose();
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        for (const material of materials as MeshBasicMaterial[]) {
          material.map?.dispose();
          material.dispose();
        }
      });
      sky.dispose();
      renderer.dispose();
    },
  };
}

/**
 * Vertex-shader breeze for vegetation: displacement grows with the baked sway
 * weight (0 at roots, 1 at tips), with slow gusts travelling across the garden.
 * Offsets are computed in world metres and divided by the node scale, since
 * quantised meshes carry a scale on their node.
 */
function addBreeze(material: Material, uniforms: { uTime: { value: number }; uBreeze: { value: number } }) {
  material.onBeforeCompile = (shader: { uniforms: Record<string, unknown>; vertexShader: string }) => {
    shader.uniforms.uTime = uniforms.uTime;
    shader.uniforms.uBreeze = uniforms.uBreeze;
    shader.vertexShader = `attribute float _sway;\nuniform float uTime;\nuniform float uBreeze;\n${shader.vertexShader}`
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vec3 swayWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;
        float gust = 0.5 + 0.5 * sin(dot(swayWorld.xz, vec2(0.32, 0.21)) - uTime * 1.1);
        gust = gust * gust * gust;
        float flutter = sin(uTime * 2.3 + swayWorld.x * 1.9 + swayWorld.z * 1.3) * 0.6
                      + sin(uTime * 4.1 + swayWorld.y * 3.1) * 0.4;
        float amp = _sway * _sway * (0.01 + 0.045 * gust) * uBreeze;
        vec3 swayScale = vec3(length(modelMatrix[0].xyz), length(modelMatrix[1].xyz), length(modelMatrix[2].xyz));
        transformed += vec3(amp * flutter, amp * flutter * 0.25, amp * flutter * 0.6) / swayScale;`);
  };
  material.customProgramCacheKey = () => 'pavilion-breeze';
}

export type LoadedScene = Awaited<ReturnType<typeof loadScene>>;
