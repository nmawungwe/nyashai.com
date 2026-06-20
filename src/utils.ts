// Format a date consistently across the site, e.g. "Jun 20, 2026".
export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Render a 1–5 rating as filled/empty stars. Returns '' when no rating given.
export function stars(rating?: number): string {
  if (!rating) return '';
  const full = Math.round(rating);
  return '★'.repeat(full) + '☆'.repeat(5 - full);
}
