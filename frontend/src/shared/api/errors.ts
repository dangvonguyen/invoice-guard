export class UnauthenticatedError extends Error {
  constructor() {
    super('No authenticated user');
    this.name = 'UnauthenticatedError';
  }
}
