import { mergeConfig } from 'vite';
import base from './vite.config';

/**
 * Host-machine dev config.
 *
 * vite.config.ts pins 3000 with strictPort because the Caddyfile routes
 * /officer/* to web:3000 and the container must bind exactly that. On a
 * developer machine 3000 is frequently taken by something unrelated, and
 * strictPort then correctly refuses to start rather than drifting to a port the
 * proxy knows nothing about.
 *
 * This config overrides only the listen address, so the container contract in
 * vite.config.ts stays untouched. `base` is deliberately not changed: serving
 * from a different prefix locally than in the proxied environment would hide
 * exactly the class of asset-path bug that base is there to prevent.
 *
 * Serves at http://localhost:5174/officer/
 */
export default mergeConfig(base, {
  server: { port: 5174, strictPort: false },
  preview: { port: 5174, strictPort: false },
});
