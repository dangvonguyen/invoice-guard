/**
 * Formats a claim's amount as a currency string, e.g. "$412.00" for USD or
 * "412.00 XYZ" for a currency `Intl.NumberFormat` doesn't recognize.
 */
export function formatClaimAmount(amount: string, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(Number(amount));
  } catch {
    return `${amount} ${currency}`;
  }
}
