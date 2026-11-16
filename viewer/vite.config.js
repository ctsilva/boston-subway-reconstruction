import { defineConfig } from 'vite';

export default defineConfig({
  // The data built by scripts/build.py is served as-is: /plan_1897.geojson, /scenarios/...
  publicDir: '../data',
  // Keep the Autark packages out of Vite's dependency pre-bundling, as Autark's own gallery does.
  optimizeDeps: {
    exclude: ['@urban-toolkit/autk-core', '@urban-toolkit/autk-map', '@urban-toolkit/autk-plot'],
  },
  server: { port: 5199 },
});
