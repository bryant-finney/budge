// Vite + SvelteKit 3 config: the SPA build (adapter-static, hash router), the dev-server /api proxy,
// and the Vitest (jsdom) test runner.
//
// ref: https://svelte.dev/docs/kit/configuration
// ref: https://testing-library.com/docs/svelte-testing-library/setup
//
// pattern: SvelteKit options go to the sveltekit() plugin (SvelteKit 3 has no svelte.config.js)
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [
    sveltekit({
      // flat layout: routes/, lib/ and app.html sit directly in src/front-end/
      files: { src: '.' },
      // Kit 3 already writes build/index.html under the hash router; `fallback` is kept per spec §10
      // and only adds the cosmetic `adapter_fallback_overwrites` build warning.
      adapter: adapter({ fallback: 'index.html' }),
      router: { type: 'hash' },
    }),
    // browser resolve conditions + automatic cleanup between tests
    svelteTesting(),
  ],
  server: {
    proxy: {
      // the compose `api` service; no VITE_ prefix, so the value never reaches client code
      '/api': process.env.BUDGE_API_PROXY_TARGET ?? 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    include: ['{lib,routes}/**/*.{test,spec}.ts'],
    setupFiles: ['./vitest-setup.ts'],
  },
});
