import { createDepthLayer } from './pavilion-depth';

export const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

/** Largest camera offset, as a fraction of the artwork's width and height. */
const SHIFT = { x: 0.02, y: 0.013 };
/** Idle camera sway, relative to a full pointer sweep: with and without a pointer. */
const DRIFT = { pointer: 0.3, touch: 0.75 };
/** Forward camera travel when a panel opens, and how long it takes. */
const DOLLY = 0.055;
const DOLLY_MS = 900;
/** Seconds for the parallax and breeze to ease in once the scene is live. */
const ARRIVAL = 1.8;
/** Flat-image fallback: pixels of pan for a full pointer sweep. */
const FLAT_PAN = { x: -6, y: -4 };

export function createSceneMotion(pavilion: HTMLElement, plane: HTMLElement, camera: HTMLElement) {
  const canPoint = window.matchMedia('(hover: hover) and (pointer: fine) and (min-width: 1101px) and (min-aspect-ratio: 4/3)');
  const canvas = plane.querySelector('canvas');
  const image = plane.querySelector('img');
  const depth = canvas && image ? createDepthLayer(canvas, image, syncLive) : null;
  // Pointer position, -1..1 from the viewport centre, and its eased value.
  let x = 0;
  let y = 0;
  let targetX = 0;
  let targetY = 0;
  let frame = 0;
  let last = 0;
  let clock = 0;
  let arrival = 0;
  let dolly = 0;
  let dollyFrom = 0;
  let dollyTo = 0;
  let dollyStart = 0;
  let focus = [0.6, 0.6];
  let sampled = 0;
  let sampledTime = 0;
  let degraded = false;

  const live = () => Boolean(depth?.ready) && !reducedMotion.matches;

  function tick(now: number) {
    frame = 0;
    const elapsed = (now - last) / 1000;
    const step = Math.min(elapsed, 0.05);
    last = now;
    const ease = 1 - Math.exp(-step * 4.5);
    x += (targetX - x) * ease;
    y += (targetY - y) * ease;

    if (!live()) {
      plane.style.setProperty('--pan-x', `${(x * FLAT_PAN.x).toFixed(3)}px`);
      plane.style.setProperty('--pan-y', `${(y * FLAT_PAN.y).toFixed(3)}px`);
      if (Math.abs(targetX - x) + Math.abs(targetY - y) > 0.002) request();
      return;
    }

    clock += step;
    arrival = Math.min(1, arrival + step / ARRIVAL);
    const settle = arrival * arrival * (3 - 2 * arrival);
    const travelled = Math.min(1, (now - dollyStart) / DOLLY_MS);
    dolly = dollyFrom + (dollyTo - dollyFrom) * (1 - (1 - travelled) ** 5);
    const drift = canPoint.matches ? DRIFT.pointer : DRIFT.touch;
    depth!.draw({
      shiftX: -(x + Math.sin(clock * 0.23) * drift) * SHIFT.x * settle,
      shiftY: -(y + Math.sin(clock * 0.17 + 1.3) * drift * 0.6) * SHIFT.y * settle,
      dolly: dolly * DOLLY,
      focusX: focus[0],
      focusY: focus[1],
      time: clock,
      breeze: settle,
    });

    // Halve the drawing resolution once if early frames run below ~40fps.
    if (!degraded && ++sampled > 30) {
      sampledTime += elapsed;
      if (sampled === 90) {
        degraded = true;
        if (sampledTime / 60 > 0.025) depth!.setQuality(0.6);
      }
    }
    // Behind an open panel the scene rests once the camera has arrived.
    if (!(pavilion.dataset.focus && travelled >= 1)) request();
  }

  function request() {
    if (!frame) frame = window.requestAnimationFrame(tick);
  }

  function start() {
    if (frame || reducedMotion.matches || document.hidden) return;
    last = performance.now();
    if (!degraded) sampled = sampledTime = 0;
    request();
  }

  function stop() {
    window.cancelAnimationFrame(frame);
    frame = x = y = targetX = targetY = 0;
    plane.style.removeProperty('--pan-x');
    plane.style.removeProperty('--pan-y');
  }

  function travel(to: number) {
    dollyFrom = dolly;
    dollyTo = to;
    dollyStart = performance.now();
  }

  // Show the depth layer only while it can draw and motion is welcome.
  function syncLive() {
    const on = live();
    pavilion.classList.toggle('is-live', on);
    if (!on) return;
    plane.style.removeProperty('--pan-x');
    plane.style.removeProperty('--pan-y');
    start();
  }

  pavilion.addEventListener('pointermove', (event) => {
    if (!canPoint.matches || reducedMotion.matches || pavilion.dataset.focus) return;
    targetX = (event.clientX / window.innerWidth - 0.5) * 2;
    targetY = (event.clientY / window.innerHeight - 0.5) * 2;
    start();
  });
  pavilion.addEventListener('pointerleave', () => {
    targetX = targetY = 0;
    if (!pavilion.dataset.focus && canPoint.matches) start();
  });
  canPoint.addEventListener('change', () => {
    stop();
    syncLive();
  });
  reducedMotion.addEventListener('change', () => {
    stop();
    syncLive();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      window.cancelAnimationFrame(frame);
      frame = 0;
    } else if (live()) start();
  });

  return {
    focus(section: string) {
      if (reducedMotion.matches) return;
      const point = pavilion.querySelector(`.hotspot-${section} .hotspot-dot`);
      focus = depth?.focus ?? focus;
      if (point && canPoint.matches) {
        const bounds = point.getBoundingClientRect();
        const frameBounds = plane.getBoundingClientRect();
        const centreX = bounds.x + bounds.width / 2;
        const centreY = bounds.y + bounds.height / 2;
        camera.style.setProperty('--focus-x', `${centreX}px`);
        camera.style.setProperty('--focus-y', `${centreY}px`);
        focus = [(centreX - frameBounds.x) / frameBounds.width, (centreY - frameBounds.y) / frameBounds.height];
      }
      pavilion.dataset.focus = section;
      travel(1);
      if (live()) start();
      else {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
    },
    reset() {
      delete pavilion.dataset.focus;
      targetX = targetY = 0;
      travel(0);
      if (live() || canPoint.matches) start();
      else stop();
    },
  };
}
