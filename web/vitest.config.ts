// vitest.config.ts - S1e. Merges the app's vite config; test-only settings live here.
import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config.ts';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.{ts,tsx}'],
      exclude: ['src/api/client/**', 'node_modules/**', 'dist/**'],
    },
  }),
);
