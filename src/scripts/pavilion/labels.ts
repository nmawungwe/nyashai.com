import { PerspectiveCamera, Vector3 } from 'three';

/**
 * Keeps the HTML object labels on their 3D anchors: each frame the anchor is
 * projected through the camera (including its view offset) to viewport pixels.
 * Labels behind the camera or well off-screen are hidden.
 */
export function createLabels(anchors: Map<string, Vector3>, elements: Map<string, HTMLElement>) {
  const v = new Vector3();
  const local = new Vector3();
  return {
    update(camera: PerspectiveCamera, width: number, height: number) {
      for (const [id, el] of elements) {
        const anchor = anchors.get(id);
        if (!anchor) continue;
        local.copy(anchor).applyMatrix4(camera.matrixWorldInverse);
        v.copy(anchor).project(camera);
        const onScreen = local.z < -0.05 && Math.abs(v.x) < 1.15 && Math.abs(v.y) < 1.15;
        el.style.visibility = onScreen ? 'visible' : 'hidden';
        if (!onScreen) continue;
        el.style.left = `${((v.x + 1) / 2 * width).toFixed(1)}px`;
        el.style.top = `${((1 - v.y) / 2 * height).toFixed(1)}px`;
      }
    },
    hide() {
      for (const el of elements.values()) el.style.visibility = 'hidden';
    },
  };
}
