# Local setup

Three services are needed: PostgreSQL with PostGIS, Redis, and an S3-compatible
object store. Pick one of the two paths below — you do not need both.

## Path A — native, no containers (recommended on macOS)

Lighter than a container runtime and starts faster. No Docker Desktop licence
question, no VM.

```bash
brew install postgresql@18 postgis redis minio
brew services start postgresql@18
brew services start redis
brew services start minio
```

Then create the database and enable extensions:

```bash
createdb bhumisetu
psql bhumisetu -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
psql bhumisetu -c 'CREATE EXTENSION IF NOT EXISTS ltree;'
psql bhumisetu -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto;'
```

Object storage buckets:

```bash
mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
mc mb local/bhumisetu-documents local/bhumisetu-models local/bhumisetu-holdout
```

### Version note

Homebrew ships PostGIS 3.6 built against PostgreSQL 18. `docker-compose.yml`
pins `postgis/postgis:15-3.3`. Nothing in the design depends on PostgreSQL 15
specifically — every feature used (generated columns, `daterange`, `ltree`, GiST,
`txid_current()`, `SKIP LOCKED`) works on 15 through 18. But if you use Path A
while CI uses the container, you are testing against a different engine than CI
does, and that difference will eventually explain a confusing failure. Prefer
aligning the two.

### On Linux

Substitute your package manager. Debian and Ubuntu:

```bash
sudo apt install postgresql-16 postgresql-16-postgis-3 redis-server
```

MinIO is a single binary from `min.io/download`.

## Path B — containers

The compose file describes the full topology, including the Caddy proxy that puts
both portals behind one origin.

**Docker Desktop** works but is heavy, and its licence is not free for larger
commercial use. Lighter drop-in replacements, all of which run the existing
`docker-compose.yml` unchanged:

| Tool | Notes |
|---|---|
| **Colima** | `brew install colima docker docker-compose && colima start`. Free, Lima-backed, no GUI. |
| **OrbStack** | `brew install orbstack`. Fastest and lightest on macOS; free for personal use, paid for commercial. |
| **Podman** | `brew install podman podman-compose && podman machine init && podman machine start`. Daemonless, rootless. Use `podman-compose`. |

Bring up only the data services while developing:

```bash
docker compose up -d postgres redis minio
```

Or the whole stack including the proxy:

```bash
docker compose up -d
```

## Environment

The API reads configuration from the environment. For Path A:

```bash
export DATABASE_URL="postgresql+psycopg://$(whoami)@localhost:5432/bhumisetu"
export REDIS_URL="redis://localhost:6379/0"
export OBJECT_STORAGE_ENDPOINT="http://127.0.0.1:9000"
export OBJECT_STORAGE_ACCESS_KEY="minioadmin"
export OBJECT_STORAGE_SECRET_KEY="minioadmin"
export OBJECT_STORAGE_BUCKET="bhumisetu-documents"
```

For Path B the compose file supplies these; the hostnames are service names
(`postgres`, `redis`, `minio`) rather than `localhost`.

Credentials above are development defaults and appear in
`docker-compose.yml`. They are not secrets and must not be reused anywhere real.

## API

```bash
cd bhumi-setu/apps/api
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Serves on `http://localhost:8000`. The citizen portal is server-rendered by this
same process at `/c/`.

## Officer portal

```bash
cd bhumi-setu/apps/web
npm install
npm run dev:local
```

Serves at **http://localhost:5174/officer/**.

The trailing `/officer/` is required. Vite is configured with
`base: '/officer/'` to match the Caddy route, so the bare root returns 404 by
design.

`npm run dev` uses 3000 with `strictPort`, which is what the container needs
because the Caddyfile routes `/officer/*` to `web:3000`. On a developer machine
3000 is often already taken and `strictPort` will refuse to start rather than
drift somewhere the proxy cannot reach — that is deliberate. `dev:local` exists
for that case and overrides only the listen address.

## Tests

```bash
cd bhumi-setu/apps/api && pytest              # needs PostgreSQL running
cd bhumi-setu/apps/web && npm run typecheck
```

Property tests use Hypothesis with a persistent example database, so a
counterexample found once replays on every later run.

## When something is wrong

**`POLICY_VALUE_MISSING`** — expected. No statutory periods are seeded until Q8
is confirmed (see `CONTRIBUTING.md`). Supply the value as a test fixture.

**Officer portal assets 404 behind the proxy** — `base` in `vite.config.ts` and
the Caddyfile route have drifted apart. The Caddyfile uses `handle`, not
`handle_path`, so the `/officer` prefix must survive to the dev server.

**`CREATE EXTENSION postgis` fails** — PostGIS is not installed for the
PostgreSQL version actually running. Check `psql -c 'SHOW server_version;'`
against which version PostGIS was built for.
