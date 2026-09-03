/**
 * Date formatting and conversion helpers shared across slices.
 */

/**
 * Formats a `Date` as a `YYYY-MM-DD` calendar date.
 *
 * @param date - The instant to format.
 * @param zone - Read the calendar date in local time or UTC. Defaults to `'local'`.
 * @returns The date as `YYYY-MM-DD`.
 */
export function toCalendarDate(date: Date, zone: 'utc' | 'local' = 'local'): string {
  if (zone === 'utc') return date.toISOString().slice(0, 10);

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
