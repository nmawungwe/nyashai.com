import { reducedMotion } from './reduced-motion';

/**
 * Panel dialogs and the mobile menu of the pavilion homepage.
 * Native modal dialogs provide focus trapping, Escape and focus return; this adds
 * the animated exit, backdrop dismissal and the scene hooks.
 */
export interface PanelHooks {
  /** Runs before a panel opens (e.g. a camera flight); the panel opens once it resolves. */
  beforeOpen?: (section: string, link: HTMLAnchorElement) => Promise<void> | void;
  /** Runs straight after the panel has opened. */
  afterOpen?: (section: string, link: HTMLAnchorElement) => void;
  /** Runs when a panel has finished closing. */
  onClose?: (section: string, dialog: HTMLDialogElement) => void;
}

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

// Finish a pending exit promptly if motion is disabled or the tab is hidden.
function finishExits() {
  if (reducedMotion.matches || document.hidden) closing.forEach((animation) => animation.finish());
}

export function setupPavilionPanels(hooks: PanelHooks = {}) {
  const menu = document.querySelector<HTMLDetailsElement>('.pavilion-menu');
  let opening = false;

  // Normal links still work without JavaScript or native dialog support.
  if (typeof HTMLDialogElement !== 'undefined' && 'showModal' in HTMLDialogElement.prototype) {
    document.querySelectorAll<HTMLAnchorElement>('a[data-panel]').forEach((link) => {
      const dialog = document.getElementById(`panel-${link.dataset.panel}`);
      if (!(dialog instanceof HTMLDialogElement)) return;
      link.setAttribute('aria-haspopup', 'dialog');
      link.setAttribute('aria-controls', dialog.id);
      link.addEventListener('click', async (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        if (opening || document.querySelector('.pavilion-panel[open]')) return;
        if (menu) menu.open = false;
        const section = link.dataset.panel!;
        if (hooks.beforeOpen) {
          opening = true;
          try {
            await hooks.beforeOpen(section, link);
          } finally {
            opening = false;
          }
        }
        dialog.showModal();
        hooks.afterOpen?.(section, link);
        if (menu?.contains(link)) {
          dialog.addEventListener('close', () => {
            menu.querySelector<HTMLElement>('summary')?.focus();
          }, { once: true });
        }
      });
    });

    document.querySelectorAll<HTMLDialogElement>('.pavilion-panel').forEach((dialog) => {
      const section = dialog.id.replace(/^panel-/, '');
      dialog.querySelector('[data-close-panel]')?.addEventListener('click', () => void closePanel(dialog));
      dialog.addEventListener('cancel', (event) => {
        event.preventDefault();
        void closePanel(dialog);
      });
      dialog.addEventListener('close', () => hooks.onClose?.(section, dialog));
      dialog.addEventListener('click', (event) => {
        if (event.target !== dialog) return;
        const bounds = dialog.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom) void closePanel(dialog);
      });
    });
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
}
