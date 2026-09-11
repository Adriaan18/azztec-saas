/**
 * Azztec_SaaS_web_openapi_ts_config_v1_0_1.ts  ->  web/openapi-ts.config.ts
 * Version:  1.0.1   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md §5.2 · OD-22 · Architecture §3.2
 *
 * Input is the COMMITTED OpenAPI document, not the live server: deterministic, no backend needed,
 * and "regenerate" means "the contract changed". Bump the input path when main.py bumps its version
 * and docs/api/openapi_<ver>.json is regenerated (S1d spec §8).
 *
 * @hey-api/client-fetch is bundled inside @hey-api/openapi-ts since 0.73 - named as a plugin, not
 * installed. @hey-api/typescript and @hey-api/sdk are defaults and not listed.
 *
 * Post-processing is Prettier ONLY. The ESLint post-processor runs the project's own config over
 * generated code; with @tanstack/eslint-config that is 47 house-style errors on vendor code and a
 * failed generation (2026-09-12, openapi-ts 0.99.0). Generated code is never hand-edited, so it is
 * never linted either: eslint.config.js ignores src/api/client/** for the same reason.
 *
 * Changelog:
 *   1.0.1  output.format / output.lint deprecated in 0.99 -> postProcess; ESLint dropped from it.
 *   1.0.0  Initial S1e.
 */
import { defineConfig } from '@hey-api/openapi-ts';

export const VERSION = '1.0.1';

export default defineConfig({
  input: '../docs/api/openapi_0_3_0.json',
  output: {
    path: 'src/api/client',
    postProcess: ['prettier'],
  },
  plugins: ['@hey-api/client-fetch', '@tanstack/react-query'],
});
