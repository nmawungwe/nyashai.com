export const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

export function createSceneMotion(pavilion: HTMLElement, plane: HTMLElement, camera: HTMLElement) {
  const canMove = window.matchMedia('(hover: hover) and (pointer: fine) and (min-width: 1101px) and (min-aspect-ratio: 4/3)');
  let x = 0;
  let y = 0;
  let targetX = 0;
  let targetY = 0;
  let frame = 0;

  function animate() {
    x += (targetX - x) * 0.075;
    y += (targetY - y) * 0.075;
    plane.style.setProperty('--pan-x', `${x.toFixed(3)}px`);
    plane.style.setProperty('--pan-y', `${y.toFixed(3)}px`);
    frame = Math.abs(targetX - x) + Math.abs(targetY - y) > 0.025
      ? window.requestAnimationFrame(animate) : 0;
  }

  function start() {
    if (!frame && !reducedMotion.matches) frame = window.requestAnimationFrame(animate);
  }

  function stop() {
    window.cancelAnimationFrame(frame);
    frame = x = y = targetX = targetY = 0;
    plane.style.removeProperty('--pan-x');
    plane.style.removeProperty('--pan-y');
  }

  function reset() {
    delete pavilion.dataset.focus;
    targetX = targetY = 0;
    if (canMove.matches && !reducedMotion.matches) start();
    else stop();
  }

  pavilion.addEventListener('pointermove', (event) => {
    if (!canMove.matches || reducedMotion.matches || pavilion.dataset.focus) return;
    targetX = (event.clientX / window.innerWidth - 0.5) * -12;
    targetY = (event.clientY / window.innerHeight - 0.5) * -8;
    start();
  });
  pavilion.addEventListener('pointerleave', () => {
    targetX = targetY = 0;
    if (!pavilion.dataset.focus && canMove.matches) start();
  });
  canMove.addEventListener('change', stop);
  reducedMotion.addEventListener('change', stop);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop();
  });

  return {
    focus(section: string) {
      if (reducedMotion.matches) return;
      const point = pavilion.querySelector(`.hotspot-${section} .hotspot-dot`);
      if (point && canMove.matches) {
        const bounds = point.getBoundingClientRect();
        camera.style.setProperty('--focus-x', `${bounds.x + bounds.width / 2}px`);
        camera.style.setProperty('--focus-y', `${bounds.y + bounds.height / 2}px`);
      }
      window.cancelAnimationFrame(frame);
      frame = 0;
      pavilion.dataset.focus = section;
    },
    reset,
  };
}
