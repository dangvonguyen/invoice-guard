/**
 * Formats a date-only string for display, preserving the date across time zones.
 *
 * @param dateOnly - A date in `YYYY-MM-DD` form.
 * @returns The localized date, e.g. "Aug 1, 2026".
 */
export function formatInvoiceDate(dateOnly: string): string {
  return new Date(`${dateOnly}T00:00:00Z`).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}
