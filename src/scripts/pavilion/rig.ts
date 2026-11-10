import { PerspectiveCamera, Quaternion, Vector3 } from 'three';

/** A camera pose exported from Blender (three.js Y-up space). */
export interface View {
  position: Vector3;
  quaternion: Quaternion;
  /** Vertical field of view of the design frame, degrees. */
  yfov: number;
  /** Width / height of the design frame. */
  aspect: number;
}

/** Flight time between the hero view and a destination. */
export const FLIGHT_MS = 1600;
/** Camera translation (metres) for a full pointer sweep, left/right and up/down. */
const SHIFT = { x: 0.07, y: 0.04 };
/** Idle drift relative to a full pointer sweep: with a precise pointer, and on touch screens. */
const DRIFT = { pointer: 0.3, touch: 0.75 };
/** Height of the flight arc above the straight line, metres. */
const ARC = 0.3;
/** Distance to the fixed look-at point while the camera rests in a view. */
const LOOK_DISTANCE = 8;

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

interface Pose { position: Vector3; quaternion: Quaternion; yfov: number; aspect: number; panel: number }

interface Flight { from: Pose; to: View; toPanel: number; start: number; done: () => void }

/**
 * Drives one PerspectiveCamera: resting views with pointer parallax and idle drift,
 * eased flights along a slight arc, and a projection that covers the viewport like
 * the poster (object-fit: cover) and can shift the subject left of an open panel.
 */
export function createRig(camera: PerspectiveCamera, options: { alignRight: () => boolean; panelWidth: () => number; panelHeight: () => number; touch: () => boolean }) {
  let rest: View | null = null;
  let restPanel = 0;
  let flight: Flight | null = null;
  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  let clock = 0;
  let motion = true;
  let width = 1;
  let height = 1;
  const pose: Pose = { position: new Vector3(), quaternion: new Quaternion(), yfov: 50, aspect: 1, panel: 0 };
  const target = new Vector3();
  const tmp = new Vector3();
  const right = new Vector3();
  const up = new Vector3();
  const control = new Vector3();

  function setRest(view: View, panel: number) {
    rest = view;
    restPanel = panel;
    target.set(0, 0, -LOOK_DISTANCE).applyQuaternion(view.quaternion).add(view.position);
    pose.position.copy(view.position);
    pose.quaternion.copy(view.quaternion);
    pose.yfov = view.yfov;
    pose.aspect = view.aspect;
    pose.panel = panel;
  }

  /**
   * The design frame covers the part of the viewport left of the panel, or above
   * it when the panel is a bottom sheet (all of the viewport when no panel is
   * open), like the poster's object-fit: cover. The render
   * still spans the whole canvas; whatever lies under the panel is extra view.
   */
  function project() {
    const k = pose.panel;
    const visible = Math.max(1, width - k * options.panelWidth());
    const visibleHeight = Math.max(1, height - k * options.panelHeight());
    // Cover: wider than the design keeps its horizontal extent and crops top and
    // bottom; narrower keeps its vertical extent and crops the sides.
    const wide = visible / visibleHeight >= pose.aspect;
    const frame = wide ? visible : pose.aspect * visibleHeight;
    const frameHeight = wide ? visible / pose.aspect : visibleHeight;
    // Where the design centre sits on screen: right-aligned crop at rest in
    // landscape (keeps the bench, as the poster does), centred in the clear
    // area beside or above a panel.
    const restCentre = frame > visible && options.alignRight() ? visible - frame / 2 : visible / 2;
    const centre = lerp(restCentre, visible / 2, k);
    camera.fov = pose.yfov;
    camera.aspect = pose.aspect;
    camera.setViewOffset(frame, frameHeight, frame / 2 - centre, (frameHeight - visibleHeight) / 2, width, height);
    camera.updateProjectionMatrix();
  }

  return {
    setSize(w: number, h: number) {
      width = Math.max(1, w);
      height = Math.max(1, h);
    },
    setMotion(on: boolean) {
      motion = on;
      if (!on) pointer.x = pointer.y = pointer.tx = pointer.ty = 0;
    },
    /** Pointer position, -1..1 from the viewport centre. */
    setPointer(x: number, y: number) {
      pointer.tx = x;
      pointer.ty = y;
    },
    get flying() { return flight !== null; },
    get view() { return rest; },
    /** Place the camera in a view immediately (first frame, reduced motion, resize). */
    jumpTo(view: View, panel = 0) {
      flight = null;
      setRest(view, panel);
    },
    /** Fly from the current pose to `view`; resolves on arrival. */
    flyTo(view: View, panel = 0) {
      return new Promise<void>((resolve) => {
        flight?.done();
        flight = {
          from: { position: camera.position.clone(), quaternion: camera.quaternion.clone(), yfov: pose.yfov, aspect: pose.aspect, panel: pose.panel },
          to: view,
          toPanel: panel,
          start: performance.now(),
          done: resolve,
        };
      });
    },
    /** Advance and apply the camera; returns true while anything is still moving. */
    update(now: number, dt: number) {
      if (!rest) return false;
      clock += dt;
      let moving = false;
      if (flight) {
        const t = Math.min(1, (now - flight.start) / FLIGHT_MS);
        const e = ease(t);
        const { from, to } = flight;
        control.copy(from.position).lerp(to.position, 0.5).y += ARC;
        // Quadratic Bézier: a gentle lift mid-flight, never a detour sideways.
        pose.position.copy(from.position).multiplyScalar((1 - e) ** 2)
          .addScaledVector(control, 2 * (1 - e) * e).addScaledVector(to.position, e * e);
        pose.quaternion.slerpQuaternions(from.quaternion, to.quaternion, e);
        pose.yfov = lerp(from.yfov, to.yfov, e);
        pose.aspect = lerp(from.aspect, to.aspect, e);
        pose.panel = lerp(from.panel, flight.toPanel, e);
        camera.position.copy(pose.position);
        camera.quaternion.copy(pose.quaternion);
        if (t >= 1) {
          const done = flight.done;
          setRest(flight.to, flight.toPanel);
          flight = null;
          done();
        }
        moving = true;
      } else {
        // Resting: a few centimetres of real translation, looking at a fixed point.
        const k = 1 - Math.exp(-dt * 4.5);
        pointer.x += (pointer.tx - pointer.x) * k;
        pointer.y += (pointer.ty - pointer.y) * k;
        const drift = motion && restPanel === 0 ? (options.touch() ? DRIFT.touch : DRIFT.pointer) : 0;
        const ox = (pointer.x + Math.sin(clock * 0.23) * drift) * SHIFT.x;
        const oy = (-pointer.y + Math.sin(clock * 0.17 + 1.3) * drift * 0.6) * SHIFT.y;
        right.set(1, 0, 0).applyQuaternion(rest.quaternion);
        up.set(0, 1, 0).applyQuaternion(rest.quaternion);
        camera.position.copy(rest.position).addScaledVector(right, ox).addScaledVector(up, oy);
        camera.quaternion.copy(rest.quaternion);
        if (ox || oy) camera.lookAt(tmp.copy(target));
        moving = drift > 0 || Math.abs(pointer.tx - pointer.x) + Math.abs(pointer.ty - pointer.y) > 1e-4;
      }
      project();
      camera.updateMatrixWorld();
      return moving;
    },
  };
}

export type Rig = ReturnType<typeof createRig>;
