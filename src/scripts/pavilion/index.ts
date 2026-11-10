import { setupPavilionPanels } from '../pavilion-panels';
import { reducedMotion } from '../reduced-motion';
import type { Rig } from './rig';
import type { LoadedScene } from './scene';

/**
 * Homepage scene wiring. The poster is the first paint and the fallback; the
 * three.js scene (a separate chunk, loaded after first paint) fades in over it
 * once its first frame is drawn.
 */
const BASE = '/pavilion/';
const DESTINATIONS: Record<string, string> = { projects: 'cam_projects', writing: 'cam_writing', reviews: 'cam_reviews' };

const pavilion = document.querySelector<HTMLElement>('.pavilion')!;
const stage = document.querySelector<HTMLElement>('.scene-stage')!;
const canvas = document.querySelector<HTMLCanvasElement>('.scene-canvas')!;
const labelEls = new Map<string, HTMLElement>();
document.querySelectorAll<HTMLElement>('.scene-label').forEach((el) => labelEls.set(el.dataset.panel!, el));
const canPoint = window.matchMedia('(hover: hover) and (pointer: fine)');
const portrait = window.matchMedia('(max-aspect-ratio: 1/1)');

let world: (LoadedScene & { rig: Rig; labels: ReturnType<typeof import('./labels').createLabels> }) | null = null;
let frame = 0;
let last = 0;
let resting = false;    // behind an open panel, once the camera has arrived
let focused: string | null = null;

const motionOn = () => !reducedMotion.matches;
const heroName = () => (portrait.matches ? 'cam_hero_portrait' : 'cam_hero');
/** Width of the open panel on screens wide enough to keep the scene visible beside it. */
const panelWidth = () => (window.innerWidth > 900 ? Math.min(34 * 16, window.innerWidth - 32) + 16 : 0);
/** Height of the open panel when it is a bottom sheet (phones; matches pavilion.css). */
const sheet = window.matchMedia('(max-width: 900px) and (max-aspect-ratio: 1/1)');
const panelHeight = () => (sheet.matches ? window.innerHeight * 0.62 + 8 : 0);

function request() {
  if (!frame && world && !document.hidden && !resting) frame = requestAnimationFrame(tick);
}

function tick(now: number) {
  frame = 0;
  if (!world) return;
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  const { rig, renderer, scene, camera, labels, breeze } = world;
  const moving = rig.update(now, dt);
  if (motionOn()) {
    breeze.uTime.value += dt;
    breeze.uBreeze.value = Math.min(1, breeze.uBreeze.value + dt / 1.8);
  }
  renderer.render(scene, camera);
  labels.update(camera, stage.clientWidth, stage.clientHeight);
  if (!pavilion.classList.contains('is-live')) pavilion.classList.add('is-live');
  // Keep drawing for drift and breeze; with reduced motion only while the camera settles.
  if (motionOn() || moving) request();
}

function resize() {
  if (!world) return;
  const w = stage.clientWidth;
  const h = stage.clientHeight;
  world.renderer.setSize(w, h, false);
  world.rig.setSize(w, h);
  if (!focused && !world.rig.flying) world.rig.jumpTo(world.views.get(heroName())!, 0);
  last = performance.now();
  if (resting) {
    // Redraw once at the new size even while resting behind a panel.
    resting = false;
    tick(last);
    resting = true;
  } else request();
}

async function start() {
  const probe = document.createElement('canvas');
  if (!(probe.getContext('webgl2') || probe.getContext('webgl'))) return;   // poster stays
  try {
    const mod = await import('./scene');
    const loaded = await mod.loadScene(canvas, BASE);
    const rig = mod.createRig(loaded.camera, {
      alignRight: () => !portrait.matches,
      panelWidth,
      panelHeight,
      touch: () => !canPoint.matches,
    });
    world = { ...loaded, rig, labels: mod.createLabels(loaded.anchors, labelEls) };
    rig.setMotion(motionOn());
    resize();
    last = performance.now();
    request();
  } catch (error) {
    console.warn('Pavilion scene unavailable; showing the poster.', error);
    fallback();
  }
}

function fallback() {
  pavilion.classList.remove('is-live');
  world?.labels.hide();
  cancelAnimationFrame(frame);
  frame = 0;
  world?.dispose();
  world = null;
}

setupPavilionPanels({
  async beforeOpen(section) {
    focused = section;
    pavilion.dataset.visiting = section;  // the greeting and labels step aside for the flight
    if (!world) return;
    const view = world.views.get(DESTINATIONS[section]);
    if (!view) return;
    if (motionOn()) {
      const arrival = world.rig.flyTo(view, 1);
      request();
      await arrival;
    } else {
      world.rig.jumpTo(view, 1);
      tick(performance.now());
    }
  },
  afterOpen() {
    resting = true;  // nothing moves behind the panel once the camera has arrived
  },
  onClose() {
    focused = null;
    delete pavilion.dataset.visiting;
    resting = false;
    if (!world) return;
    const hero = world.views.get(heroName())!;
    if (motionOn()) void world.rig.flyTo(hero, 0);
    else world.rig.jumpTo(hero, 0);
    last = performance.now();
    request();
  },
});

pavilion.addEventListener('pointermove', (event) => {
  if (!world || !canPoint.matches || !motionOn() || focused) return;
  world.rig.setPointer((event.clientX / window.innerWidth - 0.5) * 2, (event.clientY / window.innerHeight - 0.5) * 2);
  request();
});
pavilion.addEventListener('pointerleave', () => world?.rig.setPointer(0, 0));
reducedMotion.addEventListener('change', () => {
  world?.rig.setMotion(motionOn());
  if (world && !motionOn()) world.breeze.uBreeze.value = 0;
  request();
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    cancelAnimationFrame(frame);
    frame = 0;
  } else {
    last = performance.now();
    request();
  }
});
new ResizeObserver(resize).observe(stage);
canvas.addEventListener('webglcontextlost', (event) => {
  event.preventDefault();
  fallback();
});
window.addEventListener('pagehide', () => {
  cancelAnimationFrame(frame);
  frame = 0;
  pavilion.classList.remove('is-live');
  world?.dispose();
  world = null;
});
// Restored from the back/forward cache after pagehide disposed the scene.
window.addEventListener('pageshow', (event) => {
  if (event.persisted && !world) void start();
});

// Start after first paint so the poster is never delayed by the scene.
if (document.readyState === 'complete') requestAnimationFrame(() => void start());
else window.addEventListener('load', () => requestAnimationFrame(() => void start()), { once: true });
