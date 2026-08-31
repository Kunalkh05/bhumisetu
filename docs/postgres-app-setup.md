# PostgreSQL via Postgres.app (macOS, verified)

The setup actually in use on the development machine. Chosen over Homebrew and
over a container runtime because both failed on an Apple Silicon machine carrying
the Intel Homebrew — see the Apple Silicon section of
[`local-setup.md`](local-setup.md).

## Why the single-version 15 build

Postgres.app publishes a combined 508 MB image and per-version images. Take
**PostgreSQL 15** (100 MB): `docker-compose.yml` pins `postgis/postgis:15-3.3`,
and this build carries PostGIS 3.3.10. Development and container then run the
same engine and the same PostGIS minor, so a query that works locally works in
CI. Taking the 18 build instead would reintroduce the skew.

## Install

```bash
cd /tmp
curl -sL -o pgapp15.dmg \
  "https://github.com/PostgresApp/PostgresApp/releases/download/v2.9.6/Postgres-2.9.6-15.dmg"
hdiutil attach -nobrowse -quiet pgapp15.dmg
cp -R /Volumes/Postgres/Postgres.app /Applications/
hdiutil detach -quiet /Volumes/Postgres
```

No admin rights needed if `/Applications` is writable, and nothing is compiled.

## Initialise and start

Postgres.app normally does this when first launched from the GUI. Equivalent from
a shell:

```bash
export PGBIN="/Applications/Postgres.app/Contents/Versions/15/bin"
export PGDATA="$HOME/Library/Application Support/Postgres/var-15"

"$PGBIN/initdb" -D "$PGDATA" -U "$(whoami)" --encoding=UTF8 --locale=en_US.UTF-8
"$PGBIN/pg_ctl" -D "$PGDATA" -l /tmp/pg15.log start
```

Stop, restart, status:

```bash
"$PGBIN/pg_ctl" -D "$PGDATA" stop
"$PGBIN/pg_ctl" -D "$PGDATA" restart -l /tmp/pg15.log
"$PGBIN/pg_ctl" -D "$PGDATA" status
```

Launching the app from `/Applications` also starts it and keeps it running across
reboots, which is usually what you want day to day.

## Put the binaries on PATH

```bash
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zprofile
```

`Versions/latest` is a symlink, so this survives a Postgres.app upgrade.

## Create the database

```bash
createdb bhumisetu
psql -d bhumisetu -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
psql -d bhumisetu -c 'CREATE EXTENSION IF NOT EXISTS ltree;'
psql -d bhumisetu -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto;'
```

Alembic migration 1.2 also creates these, so this step is only needed if you
connect before running migrations.

## Verified working

Every PostgreSQL feature the design depends on, checked against this install:

| Feature | Used by | Result |
|---|---|---|
| `postgis` 3.3.10 | parcel and project geometry (§12) | installed |
| `ltree` 1.2 + GiST | jurisdiction hierarchy, `scoped()` (§8.1) | `IN.MH.PUNE.HAVELI <@ IN.MH` → true |
| `pgcrypto` 1.3 | passcode hashing (§19.2) | installed |
| `ST_Area` on `geography` | geodesic area vs recorded extent (R15.5) | 1°×1° → 12 308 778 361 m² |
| `daterange` generated column | ownership validity (§6.1) | created |
| `FOR UPDATE SKIP LOCKED` | outbox dispatch (§5.2) | works |

`ST_Area` on a `geography` returns square metres, so a degree-scale polygon
overflows `int`. Cast to `bigint`. Casting to `geography` rather than leaving the
geometry in EPSG:4326 is not optional: planar area in 4326 is square degrees,
which is meaningless for comparing against a recorded extent in hectares.

## Connection string

```bash
export DATABASE_URL="postgresql+psycopg://$(whoami)@localhost:5432/bhumisetu"
```

`initdb` ran with trust auth for local connections and no password, which is fine
for a development cluster reachable only over the loopback interface. Do not
mirror it anywhere reachable from a network.

## Redis and object storage

Not needed yet. Redis first appears at task 7.1 (sessions) and object storage at
task 15.1 (documents). Both install cleanly from Homebrew even under Rosetta,
since neither needs a source build:

```bash
brew install redis minio
brew services start redis
brew services start minio
```
