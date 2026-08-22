import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { File } from 'node:buffer';
import { afterAll, afterEach, beforeAll } from 'vitest';

import { server } from './mocks/server';

globalThis.File = File as typeof globalThis.File;

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
  sessionStorage.clear();
});

afterAll(() => {
  server.close();
});
