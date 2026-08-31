import { defineConfig } from 'vite';

/**
 * Officer portal build (design §3.4, §10.6).
 *
 * This app serves the officer portal and nothing else. The citizen portal is
 * server-rendered Jinja2 from the api service at /c/*, because R24.1's 150 KB
 * compressed budget cannot be met by a React bundle (design §10).
 *
 * `base` must stay '/officer/' and must stay in step with the proxy: the
 * Caddyfile routes /officer/* to this dev server with the prefix intact
 * (`handle`, not `handle_path`), so every emitted asset URL has to be absolute
 * under that prefix or the bundle 404s behind the proxy.
 */
export default defineConfig({
  base: '/officer/',

  server: {
    // Reachable from the proxy container, not just from inside this one.
    host: true,
    port: 3000,
    // Fail loudly instead of drifting to 3001, which the proxy does not know
    // about.
    strictPort: true,
  },

  preview: {
    host: true,
    port: 3000,
    strictPort: true,
  },
});
