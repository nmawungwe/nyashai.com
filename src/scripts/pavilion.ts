const pavilion = document.querySelector<HTMLElement>('.pavilion');
const plane = document.querySelector<HTMLElement>('.scene-plane');
const menu = document.querySelector<HTMLDetailsElement>('.pavilion-menu');

// Normal links are the fallback when JavaScript or <dialog> isn't available.
if (typeof HTMLDialogElement !== 'undefined' && 'showModal' in HTMLDialogElement.prototype) {
  document.querySelectorAll<HTMLAnchorElement>('a[data-panel]').forEach((link) => {
    const dialog = document.getElementById(`panel-${link.dataset.panel}`);
    if (!(dialog instanceof HTMLDialogElement)) return;
    link.setAttribute('aria-haspopup', 'dialog');
    link.setAttribute('aria-controls', dialog.id);
    link.addEventListener('click', (event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (menu) menu.open = false;
      dialog.showModal();
      if (menu?.contains(link)) {
        dialog.addEventListener('close', () => {
          menu.querySelector<HTMLElement>('summary')?.focus();
        }, { once: true });
      }
    });
  });

  document.querySelectorAll<HTMLDialogElement>('.pavilion-panel').forEach((dialog) => {
    dialog.querySelector('[data-close-panel]')?.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right ||
          event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
  });
}

// Movement follows the pointer only: no perpetual animation or device sensors.
// Object links move with the artwork so they remain attached to the right objects.
if (pavilion && plane) {
  const canMove = window.matchMedia('(prefers-reduced-motion: no-preference) and (hover: hover) and (pointer: fine) and (min-width: 1101px) and (min-aspect-ratio: 4/3)');
  let x = 0;
  let y = 0;
  let targetX = 0;
  let targetY = 0;
  let frame = 0;

  function animate() {
    x += (targetX - x) * 0.075;
    y += (targetY - y) * 0.075;
    plane!.style.setProperty('--pan-x', `${x.toFixed(3)}px`);
    plane!.style.setProperty('--pan-y', `${y.toFixed(3)}px`);
    if (Math.abs(targetX - x) + Math.abs(targetY - y) > 0.025) {
      frame = window.requestAnimationFrame(animate);
    } else {
      frame = 0;
    }
  }

  function start() {
    if (!frame) frame = window.requestAnimationFrame(animate);
  }

  pavilion.addEventListener('pointermove', (event) => {
    if (!canMove.matches || document.querySelector('dialog[open]')) return;
    targetX = (event.clientX / window.innerWidth - 0.5) * -12;
    targetY = (event.clientY / window.innerHeight - 0.5) * -8;
    start();
  });
  pavilion.addEventListener('pointerleave', () => {
    targetX = targetY = 0;
    if (canMove.matches) start();
  });

  function reset() {
    window.cancelAnimationFrame(frame);
    frame = x = y = targetX = targetY = 0;
    plane!.style.removeProperty('--pan-x');
    plane!.style.removeProperty('--pan-y');
  }
  canMove.addEventListener('change', reset);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) reset();
  });
}

// Close the small mobile menu on outside click or Escape.
document.addEventListener('click', (event) => {
  if (menu?.open && event.target instanceof Node && !menu.contains(event.target)) menu.open = false;
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menu?.open) {
    menu.open = false;
    menu.querySelector<HTMLElement>('summary')?.focus();
  }
});
