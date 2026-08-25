export function mapErrorMessage(
  error: Error,
  mapping: [errorClass: new () => Error, message: string][],
): string {
  for (const [ErrorClass, message] of mapping) {
    if (error instanceof ErrorClass) return message;
  }
  return error.message;
}
