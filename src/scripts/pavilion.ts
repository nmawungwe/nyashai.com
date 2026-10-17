import { createSceneMotion, reducedMotion } from './pavilion-motion';

const pavilion = document.querySelector<HTMLElement>('.pavilion');
const plane = document.querySelector<HTMLElement>('.scene-plane');
const camera = document.querySelector<HTMLElement>('.scene-camera');
const menu = document.querySelector<HTMLDetailsElement>('.pavilion-menu');
const motion = pavilion && plane && camera ? createSceneMotion(pavilion, plane, camera) : null;
const closing = new Map<HTMLDialogElement, Animation>();

// Keep the native modal open until its exit completes, preserving focus trapping.
async function closePanel(dialog: HTMLDialogElement) {
  if (!dialog.open || closing.has(dialog)) return;
  if (reducedMotion.matches || typeof dialog.animate !== 'function' || document.hidden) {
    dialog.close();
    return;
  }
  const current = window.getComputedStyle(dialog);
  dialog.dataset.closing = '';
  const animation = dialog.animate([
    { opacity: current.opacity, transform: current.transform },
    { opacity: 0, transform: 'translateX(20px)' },
  ], { duration: 200, easing: 'cubic-bezier(.4, 0, 1, 1)', fill: 'forwards' });
  closing.set(dialog, animation);
  try {
    await animation.finished;
  } catch {
    // Cancellation (including a changed motion preference) must still dismiss.
  } finally {
    if (dialog.open) dialog.close();
    animation.cancel();
    closing.delete(dialog);
    delete dialog.dataset.closing;
  }
}

// Normal links still work without JavaScript or native dialog support.
if (typeof HTMLDialogElement !== 'undefined' && 'showModal' in HTMLDialogElement.prototype) {
  document.querySelectorAll<HTMLAnchorElement>('a[data-panel]').forEach((link) => {
    const dialog = document.getElementById(`panel-${link.dataset.panel}`);
    if (!(dialog instanceof HTMLDialogElement)) return;
    link.setAttribute('aria-haspopup', 'dialog');
    link.setAttribute('aria-controls', dialog.id);
    link.addEventListener('click', (event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (document.querySelector('.pavilion-panel[open]')) return;
      if (menu) menu.open = false;
      dialog.showModal();
      motion?.focus(link.dataset.panel!);
      if (menu?.contains(link)) {
        dialog.addEventListener('close', () => {
          menu.querySelector<HTMLElement>('summary')?.focus();
        }, { once: true });
      }
    });
  });

  document.querySelectorAll<HTMLDialogElement>('.pavilion-panel').forEach((dialog) => {
    dialog.querySelector('[data-close-panel]')?.addEventListener('click', () => void closePanel(dialog));
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      void closePanel(dialog);
    });
    dialog.addEventListener('close', () => motion?.reset());
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right ||
          event.clientY < bounds.top || event.clientY > bounds.bottom) void closePanel(dialog);
    });
  });
}

// Finish a pending exit promptly if motion is disabled or the tab is hidden.
function finishExits() {
  if (reducedMotion.matches || document.hidden) closing.forEach((animation) => animation.finish());
}
reducedMotion.addEventListener('change', finishExits);
document.addEventListener('visibilitychange', finishExits);

document.addEventListener('click', (event) => {
  if (menu?.open && event.target instanceof Node && !menu.contains(event.target)) menu.open = false;
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menu?.open) {
    menu.open = false;
    menu.querySelector<HTMLElement>('summary')?.focus();
  }
});
