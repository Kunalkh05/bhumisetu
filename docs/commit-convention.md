# Commit convention

Commits are small and single-purpose. One logical change per commit, with a
subject line that says what changed rather than what file was touched.

## Format

```
type(scope): description
```

Subject line in the imperative mood, no trailing period, under 72 characters.
Body optional; use it for the *why*, not a restatement of the diff.

## Types

| Type | Use for |
|---|---|
| `feat` | New behaviour |
| `fix` | Corrected behaviour |
| `refactor` | Restructuring with no behaviour change |
| `test` | Tests only |
| `docs` | Documentation and spec documents |
| `chore` | Housekeeping, dependencies, config |
| `build` | Build tooling, Dockerfiles, compose |
| `ci` | CI pipeline |
| `perf` | Performance work with a measured result |

## Scopes

Scopes follow the subsystem boundaries in `.kiro/specs/bhumisetu/design.md`.

| Scope | Area |
|---|---|
| `spec` | requirements.md, design.md, tasks.md |
| `infra` | compose, proxy, MinIO, Redis |
| `db` | schema, migrations, session plumbing |
| `policy` | Policy_Config and PolicyResolver |
| `events` | event log, personal_datum, outbox |
| `concurrency` | Entity_Version, VersionedRepository |
| `auth` | sessions, officer and citizen identity |
| `gate` | Access_Control, ResponseGate, redaction |
| `case` | projects, acquisition cases, stage transitions |
| `parcel` | land parcels, ownership records |
| `notice` | statutory notices, deadlines |
| `objection` | objections and disposal |
| `award` | awards and payouts |
| `validation` | Validation_Engine, rules, issues |
| `doc` | document upload and storage |
| `ocr` | extraction, confidence routing, accuracy reports |
| `gis` | geometry, bbox queries, tiles |
| `ml` | features, labelling, training, prediction, monitoring |
| `priority` | Priority_Engine, intervention queue |
| `dashboard` | officer dashboard |
| `import` | bulk import |
| `retention` | retention, erasure, DSAR |
| `i18n` | Localization_Service, catalogs |
| `officer` | officer portal (React) |
| `citizen` | citizen portal (server-rendered) |

## Traceability

Where a commit implements a spec requirement, cite it in the body:

```
feat(policy): resolve values by state, act, and effective date

PolicyResolver.get() takes no default parameter — a default is how a
statutory period ends up hardcoded, which R7.2 forbids.

Requirements: 28.2, 28.4
Task: 2.2
```

## Examples

```
feat(events): externalise personal data to personal_datum references
test(gate): assert no route bypasses the serialization gate
refactor(ml): move label definition into LabelDefinition config
fix(parcel): treat open-ended ownership validity as unbounded
docs(spec): record censoring treatment in the ML label definition
build(infra): add Caddy proxy for TLS, HTTP/3, and brotli
```
