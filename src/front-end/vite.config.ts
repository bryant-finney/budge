// Vite + SvelteKit 3 config: the SPA build (adapter-static, hash router) and the dev-server /api proxy.
//
// ref: https://svelte.dev/docs/kit/configuration
//
// pattern: SvelteKit options go to the sveltekit() plugin (SvelteKit 3 has no svelte.config.js)
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

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
  ],
  server: {
    proxy: {
      // the compose `api` service; no VITE_ prefix, so the value never reaches client code
      '/api': process.env.BUDGE_API_PROXY_TARGET ?? 'http://localhost:8000',
    },
  },
});
