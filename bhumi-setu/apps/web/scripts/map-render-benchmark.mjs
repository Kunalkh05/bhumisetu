import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(__dirname, '..');
const distRoot = path.join(appRoot, 'dist');
const resultPath = path.join(appRoot, '.benchmarks', 'map-render.json');
const runs = Number(process.env.MAP_BENCHMARK_RUNS ?? 5);
const maxP95Ms = Number(process.env.MAP_RENDER_P95_MS ?? 4000);
const downloadThroughput = (5 * 1024 * 1024) / 8;
const emptyVectorTile = Buffer.alloc(0);

function contentType(filePath) {
  if (filePath.endsWith('.html')) return 'text/html; charset=utf-8';
  if (filePath.endsWith('.js') || filePath.endsWith('.mjs')) return 'text/javascript; charset=utf-8';
  if (filePath.endsWith('.css')) return 'text/css; charset=utf-8';
  if (filePath.endsWith('.svg')) return 'image/svg+xml';
  return 'application/octet-stream';
}

function percentile(values, percentileValue) {
  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.min(sorted.length - 1, Math.ceil((percentileValue / 100) * sorted.length) - 1);
  return sorted[index] ?? 0;
}

async function serveDist() {
  const tilePayloadSizes = [];
  const server = createServer(async (request, response) => {
    const url = new URL(request.url ?? '/', 'http://127.0.0.1');
    if (url.pathname.startsWith('/api/officer/gis/tiles/')) {
      tilePayloadSizes.push(emptyVectorTile.byteLength);
      response.writeHead(200, {
        'content-type': 'application/vnd.mapbox-vector-tile',
        'content-length': String(emptyVectorTile.byteLength),
      });
      response.end(emptyVectorTile);
      return;
    }

    const relative = url.pathname.startsWith('/officer/')
      ? url.pathname.slice('/officer/'.length)
      : url.pathname.slice(1);
    const target = relative.length === 0 ? 'index.html' : relative;
    const filePath = path.normalize(path.join(distRoot, target));

    if (!filePath.startsWith(distRoot)) {
      response.writeHead(403);
      response.end();
      return;
    }

    try {
      const body = await readFile(filePath);
      response.writeHead(200, { 'content-type': contentType(filePath), 'content-length': String(body.byteLength) });
      response.end(body);
    } catch {
      const body = await readFile(path.join(distRoot, 'index.html'));
      response.writeHead(200, { 'content-type': contentType('index.html'), 'content-length': String(body.byteLength) });
      response.end(body);
    }
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') {
    throw new Error('Benchmark server did not bind to a TCP port');
  }
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    tilePayloadSizes,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function runOnce(baseUrl) {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const client = await context.newCDPSession(page);
    await client.send('Network.enable');
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: 20,
      downloadThroughput,
      uploadThroughput: downloadThroughput,
    });

    await page.goto(`${baseUrl}/officer/map`, { waitUntil: 'domcontentloaded' });
    await page.getByTestId('parcel-map').waitFor({ state: 'visible' });
    await page.waitForFunction(() => typeof window.__BHUMISETU_MAP_RENDER_MS === 'number', null, {
      timeout: maxP95Ms,
    });
    const renderMs = await page.evaluate(() => window.__BHUMISETU_MAP_RENDER_MS ?? 0);
    await context.close();
    return renderMs;
  } finally {
    await browser.close();
  }
}

const server = await serveDist();
try {
  const renderTimesMs = [];
  for (let index = 0; index < runs; index += 1) {
    renderTimesMs.push(await runOnce(server.baseUrl));
  }
  const p95Ms = percentile(renderTimesMs, 95);
  const result = {
    threshold: {
      downlink_mbps: 5,
      p95_ms: maxP95Ms,
    },
    runs,
    render_times_ms: renderTimesMs,
    p95_ms: p95Ms,
    tile_payload_bytes: server.tilePayloadSizes,
    passed: p95Ms <= maxP95Ms,
  };
  await mkdir(path.dirname(resultPath), { recursive: true });
  await writeFile(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify(result, null, 2));
  if (!result.passed) {
    process.exitCode = 1;
  }
} finally {
  await server.close();
}
