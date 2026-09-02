# Implementation Plan: BHUMISETU

## Overview

Implementation follows the design's own dependency structure rather than the requirements' numbering. Four mechanisms are load-bearing — `PolicyResolver` (§4), the event log with `personal_datum` indirection (§5), `VersionedRepository` (§7), and `GatedRoute`/`ResponseGate` (§8) — and every later subsystem reads dates, appends events, writes entities, and serializes responses through them. They are built first, each with the structural test or CI guard that keeps it honest landing in the same task group, so the guards exist before there is code for them to catch.

Stack is fixed by the design's **Language and stack** section (under its Overview): Python 3.11 / FastAPI / SQLAlchemy 2.0 / Alembic, Celery on Redis, PostgreSQL 15 + PostGIS 3.3, MinIO, React + Vite for the officer portal only, with the deviations from the committed `docker-compose.yml` collected in §3.4. The citizen surface is server-rendered Jinja2 from the API service (§10).

After the four mechanisms: sessions → core domain → validation → documents and OCR → GIS → officer portal → citizen portal → synthetic dataset → ML pipeline → priority and intervention → retention and DSAR → bulk import → localization → the measurement harnesses for the requirements §2 flags as not satisfiable as written.

## Preconditions carried into every task

These are consequences of Q1, Q8, and Q10 being accepted as provisional (§1), plus Q4's threshold values remaining unconfirmed. Q1, Q4, Q8, and Q10 are now resolved as maintainer defaults, and the concrete values live in the requirements Open Policy Decisions section. They are constraints on implementation, not tasks:

- **A review-required RFCTLARR baseline is seeded; no statutory period is ever a literal.** A default RFCTLARR_2013 platform-wide (state key `'*'`) baseline IS now seeded as fixture/seed data — the period values from the requirements Q8 resolution, each flagged review-required before production use. Per-state values still refuse-and-report (R28.5, `409 POLICY_VALUE_MISSING`) until that state configures them. The invariant preserved unchanged is that no statutory period is ever a code literal, a column default, or a CHECK constraint — the AST lint of 2.6 and the schema guards of 2.7 stay in force. Task 2 ships the `policy_config` schema, the resolver, and the validators; Task 2.8 still seeds no value into product code — the baseline lives in the seed/config task (21.3). Every task that needs a deadline works against configured values, never against a legal number written into code, a column default, or a CHECK constraint.
- **The retention sweep ships disabled.** Task 25 builds `CATEGORY_MAP`, the metadata-walk classification test, the two-armed erasure path, and the DSAR handlers, and leaves `retention.sweep_enabled` false with no seeded `retention.period.*` rows. Erasure is irreversible; confirming Q10 late costs nothing, confirming it wrongly and sweeping is unrecoverable (§1.3).
- **The label definition is configuration.** No task may hardcode the stage transition in scope, the deadline baseline, the horizon length, or the censoring treatment. All four are fields on `LabelDefinition` resolved from `Policy_Config` (§14.4). Q1 is now resolved as a maintainer default (see the requirements Open Policy Decisions section for the resolved values); those values still enter only as `LabelDefinition` configuration, never as hardcoded constants.
- **No OCR confidence threshold value may be seeded.** The auto-accept, review, manual-entry, and document-rejection thresholds of Q4 are `Policy_Config` values, and no `ocr.threshold.*` row may be seeded outside test fixtures. Tasks 2.4, 2.5, 16.4, and 16.7 already build the mechanism: the validator that rejects a threshold set where review is not strictly below auto-accept, the write path that refuses a threshold change without a matching non-superseded `extraction_accuracy_report`, `review_state_for`'s refusal to assign `AUTO_ACCEPTED` unless a current report admits that threshold, and the report that states precision at every threshold held in config. A confidence score is a model output, not an accuracy measurement, so an unconfirmed threshold seeded as a default would silently admit bad extracted values into cases, parcels, and ownership records with no human review and no evidence that the precision at that threshold was ever measured. That is the failure being designed out.
- **Human-only or hardware-only obligations are preconditions, not tasks.** Confirming Q1/Q8/Q10, hand-labelling the Holdout_Set (R11.10 requires labels recorded independently of any OCR output), choosing a GPU or CPU recognizer for R11.8, and confirming the R24.3 measurement reading are named inside the tasks that depend on them.

## Tasks

- [x] 1. Substrate: package layout, Alembic baseline, and compose topology
  - [x] 1.1 Application skeleton and transactional session plumbing
    - `apps/api/app/main.py`, `app/settings.py`, and `app/db/session.py` with a `unit_of_work()` context manager that yields one session inside one transaction — §5.2's atomicity guarantee is this boundary, so it must exist before `EventLog.append`
    - `app/db/base.py` declaring `Base.metadata`; the metadata-walk tests in 2.7 and 25.2 read it, so it is the single registry of tables
    - Celery app under `apps/api/app/workers/celery_app.py` declaring the §13.7 queue topology: `ocr`, `ocr_bulk`, `ml`, `import`, `maintenance`, plus the beat schedule skeleton
    - _Requirements: 4.8_
  - [x] 1.2 Alembic baseline migration: extensions, jurisdiction hierarchy, officers and roles
    - `CREATE EXTENSION IF NOT EXISTS postgis`, `ltree`, `pgcrypto`
    - `administrative_area` (`code` PK, `area_type`, `state_key`, `parent_code`, `path ltree`) with `USING gist (path)`; `officer`; `role`; `jurisdiction_scope (role_id, area_code)`
    - Create the `bhumisetu_app` database role that task 3.1 revokes `UPDATE, DELETE` on `event` from
    - _Requirements: 2.1_
  - [x] 1.3 Compose topology changes recorded in §3.4
    - Add `proxy` (Caddy) terminating TLS with HTTP/3 and brotli enabled, routing `/officer/*` → `web:3000` and everything else → `api:8000`; brotli is load-bearing because R24.1's budget is stated in compressed bytes
    - Add `worker-beat` (celery beat) and `worker-general` (queues `import`, `maintenance`)
    - Add MinIO buckets `bhumisetu-holdout` — with an access key present only in the measurement task's environment and **absent from `worker-ocr`** — and `bhumisetu-models`
    - `web` builds with `base: '/officer/'` and serves the officer portal only; remove `apps/web/src/citizen/`
    - Stop using `JWT_SECRET` for officer and citizen sessions; retain it for `/internal/*` service tokens only
    - _Requirements: 11.10, 24.1, 27.6_
  - [x] 1.4 Migration round-trip test and property-test harness configuration
    - `alembic upgrade head` then `downgrade base` against a throwaway PostGIS database (§20.9)
    - Hypothesis settings per §20.8: minimum 100 examples, persistent example database in CI so a shrunk counterexample replays on every later run; shared domain generators module `apps/api/tests/strategies.py` with `st_devanagari_text`, `st_cadastral_polygon`, `st_share_vector`, `st_event_timeline`, `st_stage_graph`, `st_confidence` as stubs to be filled by the tasks that need them
    - _Requirements: none directly — harness for §20.8 and §20.9_

- [x] 2. Policy_Config and PolicyResolver (§4) — no subsystem may compute a date, threshold, cutoff, or weight without it
  - [x] 2.1 `policy_config` schema, resolution query, and change-control storage
    - Migration creating `policy_config` exactly as §4.1: `policy_key`, `state_key` (`'*'` for platform-wide), nullable `act_key`, `effective_from`, `value jsonb`, `justification_report_id`, `created_by`; `policy_config_unique_version` unique constraint; `policy_config_resolve` index; `policy_ocr_threshold_requires_report` CHECK
    - Rows are never updated or deleted — a change is a new row with a later `effective_from`, which is what gives R28.3 its history without a separate audit table
    - Implement the `_RESOLVE_SQL` of §4.1 with the `ORDER BY (state_key = :state) DESC, effective_from DESC` that gives a state override precedence over the platform default at the same date in one query
    - _Requirements: 28.1, 28.2, 28.3, 28.4_
  - [x] 2.2 `PolicyResolver` with no default, and `PolicySnapshot`
    - `apps/api/app/services/policy.py`: `PolicyResolver.get(key, *, state, act, as_of)` with a per-request cache and **no `default=` parameter** — a default is how a statutory period ends up hardcoded; `try_get` returns `None` explicitly for the callers that branch on absence
    - `PolicyValueMissing` carrying key, state, act, and date, mapped to `409 POLICY_VALUE_MISSING` in the §9.4 error envelope
    - `PolicySnapshot(values, resolved_at, content_hash)` — frozen and hashable, recorded against every output that must be attributable to the configuration that produced it (notice deadlines, priority scores, training runs)
    - _Requirements: 7.1, 28.4, 28.5_
    - _Property 64_
  - [x] 2.3 The stage set as data, not an enum
    - `acquisition_case.stage_key` is `text` with **no enum type and no CHECK constraint**; add `stage_set_effective_from` and `stage_entered_on` (migration lands with the case table in 8.1, columns declared here)
    - `StageGraph` parsed from the `policy.stage_set` value shape of §4.3, where `period_key` is a pointer to another policy key rather than a number
    - `stage_deadline(case, *, resolver)` resolving the graph as of `case.stage_set_effective_from` (pinned at creation, so an in-flight case stays coherent when a state's stage set changes) and the period as of `case.stage_entered_on`, not today
    - _Requirements: 5.3, 5.6, 7.2, 28.6_
  - [x] 2.4 Validator registry keyed on `policy_key` pattern
    - `validate_partitions_unit_interval` for `risk.band_cutoffs` — this is what makes `classify` total and monotone by construction rather than by re-checking at every call
    - `validate_review_below_auto_accept` for `ocr.threshold.*`; `validate_stage_graph` (reachability, at least one terminal, no non-terminal stage without successors, no orphan); `validate_non_negative_days` for `retention.period.*`; `validate_weights_normalisable` for `priority.weights` (reject negative and all-zero)
    - _Requirements: 28.7, 28.8_
    - _Property 65_
  - [x] 2.5 Policy write path with change control
    - `PolicyService.set` inserting a new row, appending a `POLICY_CHANGED` event carrying key, prior value, new value, effective-from, and officer, gated on the `config.write` permission
    - For `ocr.threshold.*`, assert beyond the CHECK constraint that the referenced `extraction_accuracy_report` is not superseded, matches the current extraction model version and script set, and actually states a precision figure at the new threshold value (§13.6); a CHECK can only require non-null
    - Enqueue the reband pass on a `risk.band_cutoffs` change (consumed by 22.10)
    - _Requirements: 2.5, 28.3, 28.9_
    - _Property 65_
  - [x] 2.6 AST lint rejecting integer literals reaching date arithmetic
    - `apps/api/tests/config_integrity/test_no_literal_period.py` walking every Python file under `apps/api/app`, `ml/src`, and `workers`, failing on a `Constant` keyword argument to any `timedelta`/`relativedelta` call (§20.7)
    - Lands now, before the subsystems it polices exist, so a hardcoded period can never be committed and later discovered
    - _Requirements: 7.2_
  - [x] 2.7 Schema guard tests: no date defaults, no day counts in CHECK constraints, no stage enum
    - `test_no_date_column_default_and_no_day_count_check` walking `Base.metadata` for `Date`/`DateTime` columns with a computed `server_default` (only `now()` is admissible), and every live CHECK constraint definition against a day-count pattern
    - `test_no_stage_enum_anywhere` asserting no `case_stage` enum type exists and no CHECK constraint mentions `stage_key`
    - _Requirements: 7.2, 28.6_
  - [x] 2.8 Effective-dated resolution and validator property tests, with statutory periods left unseeded
    - Property test: for any key and any date D the resolved value is the one whose `effective_from` is the latest at or before D, with state-specific beating platform-wide
    - Property test: a missing key refuses the dependent operation and returns the key and the date, and no code path substitutes a default
    - Property test: a cutoff set is accepted exactly when it contiguously partitions [0, 1]; an OCR threshold set exactly when review is strictly below auto-accept
    - **Seed no RFCTLARR period rows.** Ship `policy.stage_set` and period rows only as pytest fixtures. Confirming Q8 is a precondition on operating the platform, not a coding task
    - _Requirements: 28.2, 28.4, 28.5, 28.7, 28.8_
    - _Properties 13, 64, 65_

- [x] 3. Event log with `personal_datum` indirection (§5) — the sole source of the citizen timeline and of ML features
  - [x] 3.1 `event` schema, ordering indexes, and database-enforced append-only
    - Migration creating `event` per §5.1 including `occurrence_time` and `recording_time` as distinct columns, `has_pd_refs`, `entity_version_after`, `provenance`, `import_batch_id`, `corrects_event_id`, and `txid bigint DEFAULT txid_current()`
    - Indexes `event_entity_asof`, `event_case_asof`, `event_knowable`, `event_txid`; BRIN on `recording_time`; unpartitioned by the §5.1 decision
    - `REVOKE UPDATE, DELETE ON event FROM bhumisetu_app` — R4.2 is a revoked grant, not application code; additionally map the ORM model read-only so an accidental mutation raises before reaching the database
    - Ordering is `(occurrence_time, id)`; the `id` tiebreak is what makes the order total, which R17.5's determinism depends on
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 3.2 `personal_datum` table with an irreversible single-transition trigger
    - Migration creating `personal_datum` per §5.4 with `value_ciphertext bytea`, `key_version`, `erased_at`, `erasure_event_id`, and both indexes
    - Trigger rejecting any update other than `value_ciphertext → NULL` with `erased_at` set once, and rejecting un-erasure — this table is the only mutable thing in the log's read path and the mutation surface is deliberately one column
    - Per-category encryption key handling for `value_ciphertext` as defence in depth, keeping crypto-shredding available if Q10's confirmation demands it (§5.4)
    - _Requirements: 4.2, 32.12_
  - [x] 3.3 Personal-data attribute registry and the ML-feature disjointness guard
    - Create `apps/api/app/retention/categories.py` with `CATEGORY_MAP`, the `Discriminated` and `Reference` entry kinds, and `category_of(table, column, row=None)` that raises `KeyError` on an unclassified attribute — no `.get(..., default)`. Populate the personal-data entries the event log needs to externalise; task 25.2 completes it to full schema coverage and adds the metadata-walk test
    - Create `ml/src/features/registry.py` with the `FeatureExtractor` protocol's `source_attributes` declaration and an empty registry, so the seam exists before any extractor does
    - `test_features_do_not_derive_from_personal_data` intersecting every registered extractor's `source_attributes` with the personal-data attribute set and failing on any overlap. This belongs here, not with the ML tasks: it is the invariant that stops erasure from silently rewriting historical feature rows and breaking R17.5. The test also asserts every registered extractor declares `source_attributes` at all, so it fails closed rather than passing vacuously on an empty registry
    - _Requirements: 17.3, 32.2 (partial — completed in 25.2)_
    - _Property 39_
  - [x] 3.4 `EventLog.append` on the caller's session, with payload externalisation
    - `apps/api/app/db/event_log.py`: `append(session, *, event_type, entity, actor, changes, occurrence_time, entity_version_after=None, **kw)` taking the ambient session and never opening a connection, ending in `session.flush()` so a failure surfaces inside the caller's transaction
    - `_externalise_personal_data` writing a `personal_datum` row per personal-data attribute and putting `{"$pd": id}` in the payload; non-personal attributes stay inline as `{"from": …, "to": …}`; set `has_pd_refs` accordingly
    - _Requirements: 4.1, 4.3, 4.8_
    - _Property 7_
  - [x] 3.5 Read paths: `OCCURRED_BY` and `KNOWABLE_AT`, and the `$erased` payload resolver
    - `events(entity, as_of, mode)` where `OCCURRED_BY` filters `occurrence_time <= T` and `KNOWABLE_AT` filters both `occurrence_time <= T AND recording_time <= T`. The distinction is load-bearing: R4.4 permits a backdated append and R17.2 forbids an attribute that first became knowable after T, and only a both-times filter satisfies both
    - Record the mode on every consumer so a row can never be misinterpreted later
    - `PayloadResolver` collecting `$pd` ids only from rows with `has_pd_refs = true`, batch-fetching in one `= ANY(...)`, and substituting `{"$erased": {"data_category": …, "erased_at": …}}` for an erased datum while leaving actor, entity, both timestamps, and ordering straight from the untouched rows
    - _Requirements: 4.5, 4.7, 32.13_
    - _Properties 9, 84_
  - [x] 3.6 Compensating events
    - `append_correction(session, *, corrects_event_id, ...)` writing a new event that references the erroneous event's identifier while leaving the erroneous event stored unchanged; used by R4.6 corrections and by the erasure path in 25.3
    - _Requirements: 4.6_
    - _Property 8_
  - [x] 3.7 Deferred constraint trigger backstop on the eleven versioned entity tables
    - `assert_event_in_transaction()` raising unless an `event` row exists for `(TG_TABLE_NAME, NEW.id, txid_current())`; installed as a `DEFERRABLE INITIALLY DEFERRED` constraint trigger on all eleven R29.1 tables so a service that forgets to append cannot commit
    - Session flag the trigger checks, allowing the import path to disable it for the duration of a chunk (consumed by 26.2), because the trigger would otherwise fire 10 000 times per batch
    - _Requirements: 4.1_
  - [x] 3.8 Transactional outbox for non-database side effects
    - Migration creating `task_outbox` per §5.2 with `idempotency_key` unique and the partial `task_outbox_pending` index
    - `dispatch_outbox` on `maintenance`, polling under `SELECT ... FOR UPDATE SKIP LOCKED` and setting `enqueued_at`; scheduled every 2 seconds. Redis offers no transactional enqueue, so without this a rolled-back upload could leave an OCR job in flight against a document that does not exist
    - Every enqueue, SMS send, and presigned-URL issuance goes through it, which is why every task built later must be idempotent (§13.4)
    - _Requirements: 4.8, 10.5_
  - [x] 3.9 Event log property tests
    - Property test: every state change appends exactly one event carrying actor, entity, changed attributes with prior and new values, occurrence time, and a distinct recording time
    - Property test: an update or delete against a stored event is rejected on every available interface path and the row is unchanged; a correction exists only as a new appended event referencing the erroneous one
    - Property test over `st_event_timeline()` including backdated appends: history is ordered by occurrence time with a deterministic tiebreak, and the returned set for T equals exactly the events at or before T
    - Property test: an injected failure of the event append leaves stored state bit-identical to its pre-operation state, with no partial change observable
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8_
    - _Properties 7, 8, 9, 10_

- [x] 4. `VersionedRepository` (§7) — the only write path for a versioned entity
  - [x] 4.1 `entity_version` on every R29.1 entity and the `Versioned` mixin
    - Migration adding `entity_version integer NOT NULL DEFAULT 1` to `acquisition_case`, `land_parcel`, `ownership_record`, `statutory_notice`, `objection`, `award`, `payout`, `document`, `extracted_field`, `validation_issue`, and `notice_service_record` (the tables themselves land in tasks 8–15; this task owns the mixin and the version semantics)
    - `Versioned` declarative mixin so a new entity type cannot be added without a version column
    - _Requirements: 29.1_
    - _Property 67_
  - [x] 4.2 `VersionedRepository.update` — conditional UPDATE first, event append second, one transaction
    - `apps/api/app/db/versioned_repository.py` issuing `UPDATE ... WHERE id = :id AND entity_version = :expected` with `RETURNING`, then `EventLog.append` on the same session with `entity_version_after`
    - The order is the point: on the rejection path no event is ever written, so R29.5 holds structurally rather than by relying on rollback, and moving the append to a separate connection becomes impossible to do quietly
    - Strengthened predicate for a stage transition (`AND stage_key = :expected_stage`) per §7.2
    - _Requirements: 29.1, 29.3, 29.5, 29.6, 29.7_
    - _Properties 67, 69_
  - [x] 4.3 Conflict description and the error envelope
    - `_describe_conflict` returning every attribute whose stored value differs from the value the request presented as prior, each current stored value, the actor whose modification produced the current version (read from `event.entity_version_after` — without it, attributing a version to an actor means guessing from timestamps), and that modification's occurrence time
    - `_describe_field_review_conflict` additionally returning the winner's `review_state` and recorded value (R29.8)
    - `ENTITY_VERSION_CONFLICT` 409 envelope per §9.4; `If-Match` header dependency and `expected_version` request-model field
    - _Requirements: 29.3, 29.4, 29.8_
    - _Property 68_
  - [x] 4.4 Same-version race test on two real connections
    - Two-connection harness (not mocks — the guarantee under test is PostgreSQL's re-evaluation of the `WHERE` clause under `READ COMMITTED` after the first transaction commits, and a mock would test our belief about it)
    - Property test: for any two requests presenting the same version, exactly one commits; for a stage transition exactly one transition is recorded; for a field review the rejection carries the winner's state, value, and officer
    - Property test: a rejected modification leaves the entity bit-identical attribute for attribute and appends no event
    - _Requirements: 29.5, 29.6, 29.7, 29.8, 29.10_
    - _Properties 69, 70_
  - [x] 4.5 Static uniformity checks (R29.10)
    - Test enumerating every mutating route on `app.routes` and asserting each declares `expected_version` in its request model or an `If-Match` dependency
    - Static check that no module outside `app/db/` imports `sqlalchemy.update` or executes an `Update` against a versioned table, so the officer API, the citizen API, the Import_Service, and internal calls all reach the same code
    - _Requirements: 29.10_
    - _Property 70_

- [x] 5. `GatedRoute` and `ResponseGate` (§8) — must exist before the first endpoint
  - [x] 5.1 `Principal`, `authenticate()`, and `scoped()`
    - `apps/api/app/security/access.py`: frozen `Principal` with `kind`, `id`, `role_ids`, `permissions`, `scope_paths` (ltree, officers), `case_id` and `owner_record_ids` (citizens)
    - One `authenticate()` dependency recognising an officer cookie, a citizen cookie, or a service token and returning a `Principal`. **Nothing downstream branches on request origin** — that is how R2.7 holds for the officer portal, the citizen portal, and a direct call alike
    - `scoped(stmt, principal, area_col)` applying `AcquisitionCase.id == principal.case_id` for citizens and an ltree `descendant_of` disjunction over `scope_paths` for officers; the one composable clause applied to every scope-restricted query
    - Resolve permissions and scope from the database on each request keyed by the session's officer id, never cached in the session record — this is what makes R2.6 true
    - _Requirements: 2.1, 2.2, 2.6, 2.7, 3.7_
    - _Properties 4, 5, 6_
  - [x] 5.2 `Visibility`, `Sensitive`, `GatedModel`, and `ResponseGate.apply`
    - `apps/api/app/security/gate.py`: `Visibility` (`PUBLIC`, `OWNER_ONLY`, `OFFICER_ONLY`, `PERMISSION`), the `Sensitive(...)` field factory carrying `visibility`, `mask`, `permission`, and `data_category` in `json_schema_extra`
    - `ResponseGate.apply` walking the response model's fields, computing the failed field paths, and producing the body via `model_dump(exclude=...)` so a redacted field is **absent from the JSON**, not null and not merely unrendered
    - `mask="TRAILING_4"` applied by the gate on the serialized value so the full value never enters the response object and an endpoint author cannot forget it
    - _Requirements: 26.5, 26.7_
    - _Properties 60, 61_
  - [x] 5.3 `GatedRoute` route class and the four routers
    - `GatedRoute(APIRoute)` wrapping the inner handler and passing every response through `ResponseGate.apply` with `request.state.principal`
    - `officer_router` (`/api/officer`), `citizen_router` (`/api/citizen`), `citizen_html` (`/c`), `internal_router` (`/internal`) all constructed with `route_class=GatedRoute`, so an endpoint registered on them is gated whether or not the author thought about it
    - Jinja2 templates render the **gated** dict, so a template physically cannot print a co-owner's `owner_name` — the key is not in its context
    - _Requirements: 2.7, 26.7_
  - [x] 5.4 Route-table test
    - `test_every_route_is_gated` iterating `app.routes` and asserting each is a `GatedRoute` whose `response_model` subclasses `GatedModel`; a handler returning a bare `dict` or a `JSONResponse`, a model without visibility annotations, or a router created without `route_class` fails the build
    - _Requirements: 26.7_
  - [x] 5.5 Field-coverage test against the personal-data registry
    - `test_no_unannotated_sensitive_field` intersecting every `GatedModel` field name with the personal-data attribute set from `CATEGORY_MAP` (task 3.3) and asserting every match carries a `Sensitive(...)` annotation — adding `contact_mobile` to a response model without annotating it fails the build
    - `test_redaction_matrix_is_exhaustive` over every field of every gated model against `OFFICER`, `OWNER`, `NON_OWNER`, and `SERVICE` principals, asserting presence exactly where the annotation permits it
    - _Requirements: 26.1, 26.3, 26.4, 26.6, 26.7_
    - _Property 60_
  - [x] 5.6 Permission registry and the generated RBAC matrix
    - `PERMISSIONS = {case.transition, config.write, import.submit, validation.waive.BLOCKING, validation.waive.MAJOR, model.administer, dsar.dispose}`
    - `test_rbac_matrix_is_exhaustive_and_declared` deriving every `(route, role, in_scope)` triple from `app.routes` × `ALL_ROLES` and failing on any triple without a declared expectation, so a new route or a new permission cannot pass untested
    - `NOT_AUTHORISED` 403 with no body detail, plus an `ACCESS_DENIED` event (R2.3)
    - _Requirements: 2.3, 2.4, 2.5, 2.8, 14.6, 31.12_
    - _Properties 4, 5_

- [x] 6. Checkpoint — load-bearing mechanisms
  - Ensure all tests pass, ask the user if questions arise. Before proceeding, confirm the AST lint, the schema guards, the route-table test, the field-coverage test, the same-version race test, and the feature/personal-data disjointness test all run in CI and all fail when deliberately violated. Everything after this point is written on top of these four mechanisms.

- [x] 7. Sessions, authentication, and citizen access
  - [x] 7.1 Redis-backed opaque officer sessions
    - `apps/api/app/security/auth.py`: 256-bit opaque token in an `HttpOnly; Secure; SameSite=Strict` cookie, Redis record with 60-minute **sliding** expiry, deleted on sign-out; double-submit CSRF token on all mutations
    - Not JWT, per the §3.4 deviation: R1.5 needs immediate revocation and R2.6 needs a role change to apply on the next request, and a self-contained token satisfies neither without a revocation list, which is a session store with a larger cookie
    - `OFFICER_SIGNED_IN` and `OFFICER_SIGNIN_FAILED` events; unauthenticated responses omit every case attribute
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6_
    - _Properties 1, 7_
  - [x] 7.2 Redis token-bucket rate limits and lockouts
    - `auth:fail:{officer_id}` at 5 per 15 minutes then a 15-minute lock with an `OFFICER_ACCOUNT_LOCKED` event; `otp:mobile:{hmac}` at 5 per 60 minutes; `otp:verify:{case_ref}` at 10 per 24 hours with a `CITIZEN_ACCESS_LOCKED` event; per-session ceiling
    - Keys are always over an HMAC of the identifier so raw mobile numbers never land in Redis
    - _Requirements: 1.3, 3.5, 3.6_
    - _Property 3_
  - [x] 7.3 Sign-in indistinguishability test
    - Assert a submission for a non-existent identifier and a wrong credential for an existing one return identical status, body, and header set (§20.6)
    - _Requirements: 1.2_
    - _Property 2_
  - [x] 7.4 Citizen access service: passcode issue on a constant-time path
    - `apps/api/app/services/citizen_access.py` per §19.2: generate and Argon2id-hash the passcode **unconditionally** so the dominant CPU cost is branch-independent; send SMS through the outbox in both branches so the provider's latency never appears in either path; `pad_to_floor` absorbing the residual insert cost, with `OTP_RESPONSE_FLOOR_MS` calibrated from the measured positive-path p50
    - `ownership_record.contact_mobile_hash` lookup, 6-digit passcode, 10-minute validity, single use, per-case-reference attempt counter
    - `CITIZEN_PASSCODE_ISSUED` and `CITIZEN_PASSCODE_REFUSED` events; identical response body in both branches
    - _Requirements: 3.1, 3.4, 3.8_
    - _Property 87_
  - [x] 7.5 Citizen sessions with 15-minute absolute expiry
    - Same token shape, Redis `EX 900`, **absolute not sliding**, so a session cannot be extended indefinitely by activity; value carries `case_id` and the owner record ids the session may see
    - `Access_Control` rejects any request from the session for a different case (R3.7)
    - Events for every session issue, every citizen document retrieval, and every refused access attempt
    - _Requirements: 3.2, 3.3, 3.7, 3.8_
    - _Properties 1, 4, 7_
  - [x] 7.6 OTP timing property test
    - 200 samples on each of the matching and non-matching paths, asserting the medians are within 200 ms and the bodies and statuses are identical (§20.6). A perfectly constant-time response is not achievable in Python against PostgreSQL; the requirement asks for within 200 ms of the median, which is measurable
    - Property test over the lockout boundaries: refused exactly once the configured count is reached inside the window, refused for the configured duration, permitted afterwards
    - _Requirements: 1.3, 3.4, 3.5, 3.6_
    - _Properties 3, 87_

- [x] 8. Projects, acquisition cases, and stage transitions
  - [x] 8.1 `project` and `acquisition_case` migrations
    - `project` with `area_code`, `purpose_category`, `sanctioned_extent`, `geom geometry(MultiPolygon, 4326)` and its GiST index
    - `acquisition_case` per §6.1 including `stage_key text` with no enum and no CHECK, `stage_set_effective_from`, `stage_entered_on`, `stage_deadline`, `deadline_breached`, `is_terminal`, `terminal_event_id`, the four denormalised counters, the `risk_*` and `priority_*` columns, and the `case_queue` and `case_rescore` partial indexes
    - _Requirements: 5.1, 5.2_
  - [x] 8.2 Case creation and the stage transition service
    - `apps/api/app/services/case.py`: unique `Case_Reference` assignment, first stage from the resolved stage set, `CASE_CREATED` event, `stage_set_effective_from` pinned at creation
    - Transition validated against the resolved stage graph, rejecting with `STAGE_TRANSITION_INVALID` carrying the permitted successor set; rejecting with `BLOCKING_ISSUES_OPEN` carrying issue identifiers when `open_blocking_count > 0`; refusing a transition out of the first stage with no associated parcel
    - Transition event carries prior stage, new stage, the officer-entered occurrence date, and the officer; deadline recomputed from the config effective on the transition occurrence date
    - Routed through `VersionedRepository.update` with the strengthened stage predicate, gated on `case.transition`
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 14.2, 29.7_
    - _Properties 7, 11, 15_
  - [x] 8.3 Case list, case read, and officer timeline endpoints
    - `GET /cases` and `GET /cases/{id}` through `scoped()`; `GET /cases/{id}/timeline` reading the event log with `OCCURRED_BY` ordering
    - _Requirements: 2.2, 2.3, 23.4_
    - _Properties 4, 9, 31_
  - [x] 8.4 Stage transition and scope property tests
    - Property test over `st_stage_graph()`: a transition succeeds exactly when the target is a declared successor, no open `BLOCKING` issue exists, and the first-stage parcel guard is satisfied; a rejection returns the permitted successors or the blocking issue ids
    - Property test: every element of every scope-restricted collection lies within the principal's scope, no in-scope element is omitted, and an out-of-scope request carries no resource attribute
    - _Requirements: 2.2, 2.3, 5.3, 5.4, 5.7, 5.8, 14.2_
    - _Properties 4, 11_

- [x] 9. Land parcels and ownership records
  - [x] 9.1 `land_parcel`, `case_parcel`, and `ownership_record` migrations
    - `land_parcel` with the six-column identity, `village_norm` generated with `normalize(village, NFC)` **for matching only, never display or export**, `extent`/`extent_unit`, `geom`, `geodesic_area_sqm`; the `parcel_identity` unique index over `coalesce(sub_division, '')` serving R6.2, R6.3, and R30.9 from one constraint; `parcel_geom_gist`; `parcel_dup_scan`
    - `ownership_record` with `validity daterange GENERATED ALWAYS AS (daterange(valid_from, valid_to, '[]')) STORED`, `ownership_validity_gist` on `(parcel_id, validity)`, `ownership_mobile_hash`
    - **No exclusion constraint on `(parcel_id, owner_identity_key, validity)`**, per §6.1's explicit rejection: R13.5 requires an overlapping same-owner validity period to raise a Validation_Issue, and an exclusion constraint would reject the write instead, contradicting the requirement and breaking the import's partial-commit semantics. The GiST index exists for querying and for the detection rule
    - _Requirements: 6.1, 6.2, 6.4_
  - [x] 9.2 Parcel and ownership write paths
    - Parcel creation rejecting a duplicate identity with `DUPLICATE_PARCEL` carrying the matching identifier; ownership creation recording owner name, interest type, share, validity start, optional validity end, and contact details
    - Supersession setting `valid_to` and retaining the superseded record retrievably
    - _Requirements: 6.1, 6.3, 6.4, 6.7_
    - _Properties 12, 13_
  - [x] 9.3 Ownership-as-of-date query
    - `GET /parcels/{id}/ownership?on={date}` using `validity @> :d::date` over the GiST index; the `'[]'` bounds make an open-ended record an unbounded range, so the still-current case needs no `COALESCE` or `OR`
    - _Requirements: 6.8_
    - _Property 13_
  - [x] 9.4 Identity-uniqueness and temporal-retrieval property tests
    - Property test: a parcel write succeeds exactly when the six-column identity does not match a stored parcel, and a rejection returns the matching identifier — asserted identically for manual entry and (once task 26 lands) for a row inside a batch and two rows inside one batch
    - Property test: for any parcel and date D the returned ownership records are exactly those whose validity includes D, and superseded records remain retrievable with their end date set
    - _Requirements: 6.2, 6.3, 6.7, 6.8_
    - _Properties 12, 13_

- [x] 10. Statutory notices and the deadline sweep
  - [x] 10.1 `statutory_notice`, `notice_parcel`, and `notice_service_record` migrations
    - `response_deadline` frozen at issue with `policy_snapshot_hash` recording which configuration produced it — this is what makes R7.8 structural rather than a rule someone has to remember
    - `notice_service_record.service_location geometry(Point, 4326)` (R15.2)
    - _Requirements: 7.3, 7.5, 15.2_
  - [x] 10.2 Notice issue and service recording
    - `apps/api/app/services/notice.py`: issue records notice type, issuing authority, issue date, publication mode, and affected parcels with a `NOTICE_ISSUED` event; deadline computed as the issue date advanced by the period effective **on the issue date**
    - Service recording captures service date, service mode, and the recipient ownership record
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
    - _Properties 7, 15_
  - [x] 10.3 `deadline_sweep` on the `maintenance` queue
    - Hourly via beat: mark `deadline_breached` and append `DEADLINE_BREACHED` while the current date is at or after the stage deadline and the case remains in that stage; append exactly one `DEADLINE_APPROACHING` per crossed 30/14/7-day boundary carrying the remaining day count
    - Idempotent by construction so redelivery cannot double-append
    - _Requirements: 7.6, 7.7_
    - _Property 16_
  - [x] 10.4 Notice ordering, deadline-freezing, and deadline-state property tests
    - Property test: a computed deadline equals the governing event date advanced by the period effective on that event date, and a later change to that period leaves deadlines for earlier events unchanged while later events use the new value
    - Property test: breach state is set exactly while the condition holds, and exactly one approaching event exists per crossed boundary with the correct remaining count
    - `GET` returning the ordered notice set with issue date, service date, response deadline, and breach state
    - _Requirements: 7.1, 7.4, 7.6, 7.7, 7.8, 7.9, 28.6_
    - _Properties 15, 16_

- [x] 11. Objections
  - [x] 11.1 `objection` migration and intake
    - Objecting person, related ownership record where one exists, receipt date, grounds category, free-text substance, governing notice, `window_state`, `disposal_deadline`, `is_disposal_overdue`
    - Receipt date evaluated against the governing notice's response deadline to set within-window or out-of-window
    - _Requirements: 8.1, 8.2_
    - _Property 15_
  - [x] 11.2 Disposal, overdue marking, and counts
    - Disposal records outcome, date, reasons, deciding officer, and an `OBJECTION_DISPOSED` event; a disposal without recorded reasons is rejected with the missing-field identifier
    - Overdue marking while undisposed and past the configured disposal deadline, via the same `maintenance` sweep as 10.3
    - Per-case counts by disposal state and overdue count, maintained on `acquisition_case.undisposed_objection_count` in the same transaction as the change
    - _Requirements: 8.3, 8.4, 8.5, 8.6_
    - _Properties 7, 15, 16_

- [x] 12. Awards and payouts
  - [x] 12.1 `award`, `award_component`, and `payout` migrations
    - `numeric(18,2)` throughout, never floating point; `disbursement_state`; `ON DELETE RESTRICT` on components
    - _Requirements: 9.1_
  - [x] 12.2 Award recording and arithmetic consistency
    - Itemised components with label and amount, total, currency, determination date, determining authority. BHUMISETU records amounts determined outside the platform and verifies internal consistency only (Q9) — no market value, multiplier, or solatium computation
    - Total-versus-components tolerance of 0.01 checked with `Decimal`, so the comparison is exact rather than subject to binary representation error
    - _Requirements: 9.1, 9.2_
  - [x] 12.3 Payout recording, ceiling enforcement, and derived disbursement state
    - `PAYOUT_RECORDED` event; a payout that would push the running sum past the award total is rejected with `PAYOUT_EXCEEDS_AWARD` carrying the remaining disbursable amount
    - `UNPAID` / `PART_PAID` / `FULLY_PAID` derived from the payout sum; per-case aggregate awarded and disbursed maintained transactionally on `acquisition_case`
    - Property test over any payout sequence: each is accepted exactly while the running sum would not exceed the total, and at every prefix the derived state matches
    - _Requirements: 9.4, 9.5, 9.6, 9.7_
    - _Properties 7, 17_

- [x] 13. Validation engine
  - [x] 13.1 `validation_issue` and `validation_issue_history` migrations
    - `fingerprint text` plus the **partial unique index** `validation_issue_open_unique (case_id, rule_id, fingerprint) WHERE resolution_state = 'OPEN'` — making idempotence a constraint rather than a service-layer check-then-insert removes the race between two concurrent evaluations and removes the possibility of a rule author forgetting the check
    - `validation_issue_queue` partial index for the ordered queue
    - _Requirements: 13.6, 13.8, 14.1, 14.7_
  - [x] 13.2 `Rule`, `RuleContext`, and the two context implementations
    - `apps/api/app/services/validation/`: frozen `Rule` with `rule_id`, `kind`, `severity_key` resolved through `PolicyResolver` (never a literal — R28.1 puts per-rule severity in configuration), `evaluate`, and a deterministic `fingerprint` over `(rule_id, sorted entity refs)`
    - `RuleContext` protocol with `DbRuleContext` (queries per lookup) and `ChunkRuleContext` (answers from a preloaded dict). Building both now is what makes R30.3 possible without an import-specific validation path that would drift within a release or two
    - _Requirements: 13.6, 14.1, 28.1, 30.3_
  - [x] 13.3 The rule set
    - Required-field rules over the fields the configured rule set marks mandatory at the current stage; date-chronology rules over declared predecessors; cross-document consistency over a field appearing in more than one document of the same case; duplicate detection over parcels sharing state/district/tehsil/village/survey number and over ownership records sharing an owner identity on one parcel with overlapping validity
    - The four tolerance rules — share sum 1 ± 0.0001, award total ± 0.01, geodesic area within 5 %, same-case parcel overlap within 1 % — share one implementation parameterised by tolerance key, which is why they collapse into a single property. The geometry two are wired in task 17.4 once PostGIS area exists
    - _Requirements: 6.5, 6.6, 9.2, 9.3, 13.2, 13.3, 13.4, 13.5_
    - _Properties 14, 29_
  - [x] 13.4 Evaluation trigger, issue creation, and derived resolution
    - Evaluate the configured rule set on an extracted-field review-state change, an ownership change, a parcel change, an award change, or a stage change
    - After evaluation, any open issue whose `(rule_id, fingerprint)` is absent from the new violation set moves to `RESOLVED_BY_CORRECTION` with a history row and an event — resolution is derived from the rule passing, not from an officer asserting it passed
    - Swallow the benign duplicate-key from the partial unique index on a concurrent evaluation
    - Maintain `open_blocking_count` on `acquisition_case` in the same transaction
    - _Requirements: 13.1, 13.6, 13.7, 13.8, 14.4_
    - _Properties 28, 29_
  - [x] 13.5 Issue queue, waiver, and resolution history
    - `GET /issues` ordered by severity descending then detection time ascending, scoped; `POST /issues/{id}/waive` requiring a non-empty reason, setting `WAIVED`, appending an event with officer, reason, and occurrence time, and permitting a `BLOCKING` waiver only with `validation.waive.BLOCKING`
    - `GET` returning the ordered resolution history with each state change, acting officer, reason where recorded, and occurrence time; issues retained retrievably after resolution
    - _Requirements: 14.3, 14.5, 14.6, 14.7, 14.8_
    - _Properties 5, 30, 31_
  - [x] 13.6 Validation property tests
    - Property test: a second evaluation over unchanged data produces an identical issue set with no additional issue created, and an issue becomes `RESOLVED_BY_CORRECTION` exactly on the first evaluation at which its rule no longer violates
    - Property test over `st_share_vector()` and generated award component vectors: for each configured tolerance rule, an issue of the severity declared in config exists exactly when the tolerance is exceeded and names the offending entities
    - Property test: exactly one severity from the four is assigned and the issue carries rule id, offending entity ids, observed values, and detection time
    - Property test: history is returned in order and the issue remains retrievable after resolution; a waiver without a reason is refused
    - _Requirements: 6.5, 6.6, 9.2, 9.3, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 14.1, 14.3, 14.4, 14.5, 14.7, 14.8_
    - _Properties 14, 28, 29, 30, 31_

- [x] 14. Checkpoint — core domain and validation
  - Ensure all tests pass, ask the user if questions arise. At this point a case can be created, progressed against a configured stage graph, blocked by a `BLOCKING` issue, and every write carries a version check and an event.

- [x] 15. Documents and MinIO access grants
  - [x] 15.1 `document` migration and `Document_Service.store()`
    - `document` per §6.1 with `checksum_sha256 bytea`, `object_key`, `processing_state`, `failure_reason`, `detected_script`, the `CHECK (case_id IS NOT NULL OR parcel_id IS NOT NULL)`, and the partial unique index `document_case_checksum (case_id, checksum_sha256) WHERE case_id IS NOT NULL` scoping duplicate rejection per case
    - `store()` admitting PDF, JPEG, PNG, TIFF up to 25 MB, rejecting with the applicable limit or the accepted set, rejecting a duplicate checksum with `DUPLICATE_DOCUMENT` carrying the existing id, putting the object, inserting the row as `QUEUED`, appending `DOCUMENT_UPLOADED`, and inserting the extraction task into the outbox — all in one transaction so nothing is enqueued if the transaction rolls back
    - This is the single function the officer endpoint and the import path both call, so R30.10 is the same code rather than a re-implementation
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 30.10_
    - _Properties 7, 12, 20_
  - [x] 15.2 Presigned grants and grant events
    - `GET /documents/{id}/grant` issuing a MinIO presigned URL with `expires_in` at most 900 seconds; buckets deny anonymous access; a startup assertion and a test both check `PRESIGN_TTL_SECONDS <= 900` because the requirement is a number in configuration and configuration drifts
    - Every grant issue appends an event carrying the requesting actor and the document
    - _Requirements: 10.6, 10.7, 25.6_
    - _Properties 7, 19_
  - [x] 15.3 Byte immutability
    - Uploaded bytes are never rewritten; extraction output is separate rows referencing the immutable object
    - Property test: a checksum recomputed over the stored object reproduces the recorded checksum, before and after extraction
    - Integration test against a real MinIO for presigned-URL expiry (§20.9)
    - _Requirements: 10.8, 11.9_
    - _Properties 18, 19_
  - [x] 15.4 Upload admission property test
    - Property test: an upload is accepted exactly when the content type is in the accepted set and the size is within the limit, a rejection returns the limit or the set, and the decision is identical for an officer upload and a batch document row
    - _Requirements: 10.2, 10.3, 30.10_
    - _Property 20_

- [x] 16. OCR worker, confidence routing, holdout set, and accuracy reports
  - [x] 16.1 `extraction` and `extracted_field` migrations
    - `extraction` with `UNIQUE (document_id, extraction_model_version)` — the idempotency guard that makes a redelivered `extract_document` unable to write a second extraction
    - `extracted_field` with `extracted_value` (NULL when discarded), `original_extracted_value` and `original_confidence` retained across correction, `confidence CHECK BETWEEN 0 AND 1`, page number and four page-relative coordinates, `review_state`, `accuracy_report_id` as the R11.14 gate evidence
    - _Requirements: 11.2, 11.3, 12.3, 12.7_
  - [x] 16.2 `Recognizer` protocol and the Tesseract baseline
    - `workers/ocr/`: `Recognizer` protocol with `version`, `detect_script`, `recognise`, so the engine is a deployment choice rather than an architectural one. **R11.8 is a hardware statement** (§2): CPU Tesseract with Devanagari runs 8–25 s for a 2 MB scan; a transformer recognizer needs a GPU. Choosing the deployment target is a precondition, not a task
    - Baseline: Tesseract 5 with `dev`, `eng`, and the deployment's configured third traineddata, preceded by deskew, denoise, and adaptive thresholding
    - Two-stage field extraction: full-page recognition with word-level boxes, then a field locator mapping configured target names to regions via label anchors and a per-document-type template, with field confidence aggregated from constituent word confidences
    - _Requirements: 11.2, 11.3, 11.4_
  - [x] 16.3 `extract_document` task, script gating, and retries
    - Conditional state transition `WHERE processing_state IN ('QUEUED','PROCESSING')`; `EXTRACTION_STARTED` event; `UNSUPPORTED_SCRIPT` with the detected script recorded and no retry for a script outside the configured set
    - `autoretry_for=(TransientExtractionError,)`, `retry_backoff=1`, `max_retries=3` giving four total executions at 1 s / 2 s / 4 s with jitter on so a batch failing on one transient cause does not retry in lockstep; terminal handler setting `EXTRACTION_FAILED` with the reason. A corrupt file or unsupported script is terminal on the first attempt — retrying a deterministic failure three times only delays the officer's feedback
    - _Requirements: 11.1, 11.4, 11.5, 11.6, 11.7_
    - _Properties 25, 88_
  - [x] 16.4 `review_state_for` — the only place a Review_State is assigned
    - Pure function per §13.5 returning `(review_state, reason)`: below review → `MANUAL_ENTRY_REQUIRED` with the value discarded to NULL while `original_extracted_value` and `original_confidence` are retained; below auto-accept → `PENDING_REVIEW`; at or above auto-accept → `AUTO_ACCEPTED` **only** where a non-superseded accuracy report for the current model version and script set admits that threshold, otherwise `PENDING_REVIEW` with `NO_CURRENT_ACCURACY_REPORT` or `REPORT_DOES_NOT_COVER_THRESHOLD`
    - The gate degrades to human review rather than blocking extraction; refusing to extract would strand the whole document
    - Mean-confidence below the document-rejection threshold sets `REJECTED_LOW_QUALITY` and records a re-upload request against the case
    - _Requirements: 11.14, 12.1, 12.2, 12.3, 12.4_
    - _Properties 21, 22_
  - [x] 16.5 Officer review, correction, and admission gating
    - Confirm without change → `CONFIRMED` with an event carrying the officer; change → `CORRECTED` retaining the original value and confidence, with an event carrying prior value, new value, and officer; routed through `VersionedRepository` so a double review is a conflict (R29.8)
    - `Case_Service` admits an extracted value into a case, parcel, or ownership record only while the review state is `AUTO_ACCEPTED`, `CONFIRMED`, or `CORRECTED`
    - Per-case counts of `PENDING_REVIEW` and `MANUAL_ENTRY_REQUIRED`, maintained on `pending_review_count`
    - _Requirements: 12.6, 12.7, 12.8, 12.9, 29.8_
    - _Properties 7, 26, 27_
  - [x] 16.6 Holdout set: separate bucket, separate credential, labels in PostgreSQL
    - `holdout_document` and `holdout_label` migrations; bytes in `bhumisetu-holdout` whose key is present only in the measurement task's environment. R11.10's withholding is enforced by credentials, not by a policy note
    - `ml/data/holdout/manifest.json` in git holds only document ids, script, type, and a manifest hash used to key reports — never label values, which are transcribed owner names and survey numbers and therefore live under the retention regime
    - **Hand-labelling the holdout set is a human precondition**: R11.10 requires values recorded independently of any OCR output, so the labels cannot be bootstrapped from the recognizer
    - _Requirements: 11.10_
  - [x] 16.7 `measure_extraction_accuracy` and the report
    - `extraction_accuracy_report` migration; task on `ocr_bulk` (separate queue, prefetch 1, so a 200-document measurement cannot starve interactive extraction)
    - Report states per-field exact-match accuracy, per-script accuracy, holdout document count, per-field labelled instance count, measurement date, extraction model version, and **precision at every threshold held in config**, computed over exactly the fields that threshold admits — which is not the same as overall accuracy
    - `exact_match` is `extracted.strip() == expected.strip()`: no case folding and no unicode normalisation, because a normalised match is not a character match
    - Supersession trigger on `policy_config` inserts matching `ocr.scripts.%` and on a new `extraction_model_version`, so `review_state_for` refuses `AUTO_ACCEPTED` until a superseding report exists; every report retained with its measurement date and measured version
    - Idempotent by `(extraction_model_version, script_set_version, holdout_manifest_hash)`
    - _Requirements: 11.11, 11.12, 11.13, 11.14, 11.15, 28.9_
    - _Properties 23, 24_
  - [x] 16.8 OCR property tests
    - Property test over `st_confidence()` weighted to threshold boundaries: exactly one review state is assigned for any confidence in [0, 1] and any valid threshold pair, a higher confidence never yields a state requiring more intervention, the value is absent where `MANUAL_ENTRY_REQUIRED`, and `AUTO_ACCEPTED` requires a current admitting report
    - Property test over `st_devanagari_text()` including combining marks, NFC and NFD forms, and ZWJ: the match predicate is character equality after trimming
    - Property test: report figures equal an independent recount over the same inputs
    - Property test: extraction output is complete and script-gated per Property 88; corrections preserve the original extraction across any sequence
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.11, 11.12, 11.13, 11.14, 11.15, 12.1, 12.2, 12.3, 12.4, 12.7, 12.8, 12.9_
    - _Properties 21, 22, 23, 24, 25, 26, 27, 88_

- [x] 17. GIS geometry, bbox query, tiles, and clustering
  - [x] 17.1 Geometry storage and validation
    - `apps/api/app/services/gis.py`: `store_geometry()` checking `ST_IsValid`, returning `ST_IsValidReason` and `ST_IsValidDetail` on rejection so the response carries a coordinate of the first detected invalidity; accepting polygon and multipolygon for parcels and projects and point for notice service locations; transforming to SRID 4326 on store and returning GeoJSON in WGS 84 regardless of the submitted reference system
    - `geodesic_area_sqm` from `ST_Area` on a `geography` cast — planar area in EPSG:4326 would be square degrees and meaningless
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_
    - _Property 32_
  - [x] 17.2 Bbox intersection endpoint with declared simplification
    - `GET /gis/parcels?bbox=` per §12.1: `&&` against `ST_MakeEnvelope` for the index-backed candidate reduction, then `ST_Intersects` for the exact filter, then ltree scope disjunction, `LIMIT 5000`
    - `ST_SimplifyPreserveTopology` at a viewport-derived tolerance with 6-decimal coordinate truncation. **This is what makes R15.8 achievable at all** (§2): 5000 full-fidelity cadastral polygons are ~5 MB of GeoJSON and over 8 s of transfer at 5 Mbps before serialization; simplified they are ~250–400 KB. The endpoint contract states the simplification and the tolerance in the response so a client is never misled into treating the geometry as survey-grade
    - A separate single-parcel endpoint serves full-fidelity geometry with no simplification
    - _Requirements: 15.4, 15.8_
    - _Property 33_
  - [x] 17.3 Server-side grid clustering and vector tiles
    - Cluster query per §12.2 grouping on `ST_SnapToGrid(ST_Centroid(geom), :cell_size_deg)`. **Grid snap, not `ST_ClusterKMeans`**: KMeans assignments are not stable across a small pan or zoom so markers visibly jump; grid snap is deterministic in the viewport-derived cell size. Less even cluster sizes accepted for stable rendering
    - Server-side mode switch: count first, return clusters above `gis.cluster_threshold` (config, so R16.2's 200 is not a literal) and individual features below
    - `GET /gis/tiles/{z}/{x}/{y}.mvt` via `ST_AsMVT`, cached in Redis keyed by scope hash and a parcel-geometry generation counter, with counter bump on any geometry write scoped to the affected area path so a stale tile cannot outlive a boundary correction
    - _Requirements: 16.1, 16.2, 16.3_
    - _Property 33_
  - [x] 17.4 Geometry validation rules wired into the engine
    - Area-divergence rule raising the configured severity when the geodesic area differs from the recorded extent by more than the configured fraction, converting via `extent_unit`; same-case parcel overlap rule naming both parcels above the configured fraction. Both use the shared tolerance-rule implementation from 13.3
    - _Requirements: 15.6, 15.7_
    - _Property 14_
  - [x] 17.5 PostGIS benchmark, seeded and plan-capturing
    - `apps/api/tests/perf/test_gis.py` per §20.4: session fixture generating 50 000 parcels with realistic cadastral geometry (20–80 vertices, village-clustered, overlapping bounding boxes) then `ANALYZE`; 100 bounding boxes each containing 5000 parcels; assert p95 ≤ 2 s and assert the boxes really did contain 5000
    - Capture `EXPLAIN (ANALYZE, BUFFERS)` on failure — a regression here is almost always a plan change and the plan is the diagnosis
    - Nightly at 50 000; a 5000-parcel smoke variant per PR because seeding is the slow part
    - _Requirements: 15.8_
  - [x] 17.6 Geometry property tests
    - Property test over `st_cadastral_polygon()` including deliberately self-intersecting inputs: a write succeeds exactly when the type is accepted and the geometry is topologically valid, a rejection returns a coordinate of the first invalidity, and returned geometry is in WGS 84 whatever it was submitted in
    - Property test: the returned parcels are exactly those intersecting the box and in scope, and where the count exceeds the threshold the cluster counts sum to that same count
    - Integration test of `ST_Area` on `geography` against known reference polygons (§20.9)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.8, 16.1, 16.2, 16.3_
    - _Properties 32, 33_

- [x] 18. Officer portal
  - [x] 18.1 App shell, TanStack Query data layer, and the conflict dialog
    - `apps/web/src/officer/` on React 18 + Vite + TypeScript with `base: '/officer/'`
    - Entity fetches capture `entity_version` and the mutation hook replays it as `If-Match`, so R29.2 is satisfied by the data layer rather than by per-form discipline
    - A 409 renders `ConflictDialog` showing submitted versus current per attribute and requiring a resubmit against the current version
    - _Requirements: 29.2, 29.9_
  - [x] 18.2 Case workspace
    - Present Case_Reference, project, stage, stage deadline with remaining days, parcels, currently valid ownership records, notices, objections, awards with disbursement state, open validation issues, current risk band with explanation factors, and documents — correct for a case with empty collections
    - Internal officer notes rendered only for officer principals (enforced at the gate, so the field is absent rather than hidden)
    - Three distinct card states rendered from explicit response fields and never inferred from a null: scored, not-scored, and scored-but-unmonitored
    - _Requirements: 16.8, 23.1, 23.5, 18.18, 19.12, 31.13_
    - _Properties 34, 54, 60_
  - [x] 18.3 Document viewer with bounding-box highlight
    - PDF.js for PDFs, canvas for raster; page navigation and zoom; boxes drawn from the stored page-relative coordinates so a highlight cannot drift from the recorded value
    - Extracted-field review surface presenting the value beside the source region, wired to `PATCH /fields/{id}`
    - _Requirements: 12.5, 23.2, 23.3_
    - _Property 54_
  - [x] 18.4 Map view with risk overlay
    - MapLibre GL over the MVT endpoint; viewport-scoped requests only; selection navigating to the case workspace; parcel identity, extent, Case_Reference, and stage presented for a selection without a further viewport request
    - Risk shading as a data-driven paint expression on the `risk_band` tile property with the band-to-shade legend; `risk_band: null` renders the distinct not-scored shade with its own labelled legend row
    - _Requirements: 16.1, 16.3, 16.4, 16.5, 16.6, 16.8_
    - _Property 34_
  - [x] 18.5 Validation issue queue, timeline, and processing-state surfaces
    - Ordered issue queue with waiver flow and resolution history; case timeline ordered by occurrence time; `QUEUED`/`PROCESSING` document states presented while the portal stays responsive to other requests
    - _Requirements: 11.7, 14.3, 14.5, 14.8, 23.4_
    - _Properties 30, 31_
  - [x] 18.6 Officer i18n and script display
    - `react-i18next` with per-locale chunks loaded on demand; missing keys reported to `POST /internal/i18n/missing`; the recognised script of an extraction presented alongside its fields
    - _Requirements: 27.2, 27.4, 27.7_
    - _Property 63_
  - [x] 18.7 Map render benchmark in CI
    - Throttled harness asserting initial map render p95 ≤ 4 s at ≥ 5 Mbps downlink, landing **in this task** rather than a later hardening pass, with the tile payload sizes recorded so a regression is attributable
    - _Requirements: 16.7_

- [ ] 19. Citizen portal — server-rendered, inside the transfer budget
  - [x] 19.1 Jinja2 templates and the `/c/*` routes
    - `apps/api/app/citizen/` templates rendering the **gated** payload; routes `GET /c/`, `POST /c/request-code`, `POST /c/verify`, `GET /c/case`, `GET /c/timeline?page=`, `GET /c/documents`, `GET /c/documents/{id}/confirm`, `GET /c/documents/{id}`, `GET /c/notices`, `GET /c/objections`, `POST /c/language` on `citizen_html` with `route_class=GatedRoute`
    - Not a React SPA, per §10.1: React 18 + React DOM alone is ~45 KB compressed before any application code, and an SPA pays two serial round trips before first paint, which at 2000 ms RTT costs 4 s before rendering can start
    - Timeline pagination at 20 events as plain `<a href>`; language selection as a `<form method="post">`; single-column CSS legible at 320 CSS pixels with no media queries needed below 480 px; no images in the content path and a system font stack first, so the content reads with images and web fonts failing
    - _Requirements: 24.4, 24.5, 24.10, 25.1, 25.4, 25.9, 27.3_
    - _Properties 56, 63_
  - [~] 19.2 Citizen content views
    - Case status: Case_Reference, project name, current stage in plain language, the date the stage began, the next expected step, and the configured statutory period with remaining days as plain-language text
    - Own ownership records with parcel identity, recorded extent, and share; own award total and disbursement state; notices served on the citizen with type, service date, and response deadline; own objections with receipt date, disposal state, and disposal date
    - Documents list restricted to the citizen's own ownership records and parcels with type, upload date, and byte size
    - _Requirements: 25.1, 25.2, 25.3, 25.5, 25.7, 25.8, 25.9_
    - _Property 59_
  - [~] 19.3 Redaction shapes and grant-backed document retrieval
    - `CitizenParcelOut` with `co_owner_count` and `other_share_total` and **no collection of other owners at all** — R26.2 is a different shape, not a subset, so it is a distinct model rather than gate work (§8.4)
    - Document retrieval over a time-limited grant with an event carrying the citizen session id and the document id; the confirm interstitial presents the recorded byte size before any bytes transfer
    - Every citizen data retrieval appends an event carrying session id, case id, and retrieval time
    - _Requirements: 24.9, 25.6, 26.2, 26.8_
    - _Properties 7, 19, 58, 61_
  - [~] 19.4 Service worker — the entire JavaScript budget
    - `apps/api/app/citizen/static/sw.js` per §10.2: `fetchWithRetry` with one initial attempt plus 3 retries at 1 s / 2 s / 4 s; on failure serve the Cache Storage hit with the `<!--STALE-->` marker replaced by a `data-stale-at` timestamp; with no hit, serve the precached `/c/offline` route naming the action to retry
    - The stale banner text is server-rendered in the citizen's selected language, so the worker ships no translation strings. Minified and brotli-compressed this is ~1.4 KB against a 10 KB budget line
    - **The worker only helps from the second visit onward.** A first-ever visit with no connectivity gets the browser's own error page; this is inherent to service workers and is documented in the template comment rather than implied to work
    - _Requirements: 24.6, 24.7, 24.8_
    - _Property 57_
  - [~] 19.5 Transfer budget enforced in CI, in this task
    - `apps/api/tests/perf/test_citizen_budget.py` per §10.5: brotli quality 11 to match the proxy, subresources discovered from the rendered HTML rather than a hand-maintained list, run for **every** configured citizen language since a Devanagari page is larger than an English one
    - Assert total ≤ 150 000 B, any font file ≤ 40 000 B, and every citizen JSON response ≤ 50 000 B; a size-assertion middleware enforces the 50 KB bound in test and staging
    - `maximal_case` fixture built adversarially: the configured maximum parcels per case, longest-permitted Devanagari owner names, a full 20-event timeline page, every optional field populated. A budget test that passes on a small fixture and fails in production is worse than no test
    - Runs on every PR and fails the build. This lands here, not in a later hardening pass
    - _Requirements: 24.1, 24.2, 27.6_
    - _Property 55_
  - [~] 19.6 Font strategy with a build-step cap
    - Default path ships **no font**: the stack is `system-ui, "Noto Sans Devanagari", "Noto Sans", sans-serif`, and Android has shipped Devanagari system fonts since 4.x. Cost 0 KB, and R27.6 is satisfied trivially because no font file is transferred
    - Where a deployment requires a typeface, a glyph-subset WOFF2 restricted to the Unicode block plus the required conjunct set with hinting and unused OpenType features stripped, declared `unicode-range` and `font-display: swap` so it never blocks first paint; a build step fails if the produced file exceeds 40 KB
    - Content-based subsetting is unavailable because the page renders arbitrary owner and village names. **If a confirmed Q7 regional script has no viable ≤ 40 KB subset and weak device coverage, R27.6 and R24.1 conflict for that deployment** — the build step failing is the signal to raise it, not to quietly ship an oversized file
    - _Requirements: 27.6_
    - _Property 55_
  - [~] 19.7 Citizen property tests
    - Property test: rendered without images and without web fonts, every declared content item is present as text; timeline pages of 20 cover the citizen-visible event set exactly once with no gap and no duplicate
    - Property test: a failing request retries at most 3 times with strictly increasing delays from 1 s, and the presented cached content equals what was cached, with its retrieval time and a stale label
    - Property test: the byte size presented before transfer equals the recorded size and no bytes transfer without explicit confirmation
    - Property test: the ownership records, awards, payouts, documents, notices, and objections in every response are exactly those held by, served on, or raised by the session owner, with values equal to stored values
    - Property test: the full stored government identifier appears nowhere in any citizen response body and at most its trailing 4 characters appear; every other owner's name is absent
    - Example test for the cold-offline path (no cache, no registered worker)
    - _Requirements: 24.5, 24.6, 24.7, 24.8, 24.9, 24.10, 25.2, 25.3, 25.5, 25.7, 25.8, 26.1, 26.2, 26.5, 26.6_
    - _Properties 56, 57, 58, 59, 60, 61_

- [~] 20. Checkpoint — both portals
  - Ensure all tests pass, ask the user if questions arise. Confirm the citizen transfer budget test and the officer map benchmark are both green in CI and both fail when a regression is introduced deliberately.

- [ ] 21. Synthetic dataset for point-in-time replay and training
  - [~] 21.1 Event-timeline generator with realistic recording lag
    - `scripts/seed/synthetic.py` generating a district of 10 000 cases across the configured stage graph, with per-case event timelines where `recording_time` lags `occurrence_time` by a realistic distribution and a fraction of events are **backdated** — appended with an occurrence time earlier than an already-stored event for the same entity
    - Backdated events are what make the `KNOWABLE_AT` versus `OCCURRED_BY` distinction observable; without them a point-in-time replay test cannot distinguish the two predicates and passes vacuously
    - _Requirements: 4.4, 17.1, 17.2_
  - [~] 21.2 Enough closed cases to train and evaluate
    - Generate at least the volume needed for a temporal split with a non-degenerate base rate on both sides: cases reaching a terminal stage with varied stage durations relative to their configured deadlines, so labelling yields `DELAYED`, `NOT_DELAYED`, and `CENSORED` rows in meaningful proportions, plus per-district counts spanning the minimum district calibration count so R19.6 and R19.7 are both exercisable
    - Parcels with cadastral geometry, ownership vectors summing inside and outside tolerance, awards with consistent and inconsistent component sums, documents with extractions across the confidence range
    - _Requirements: 18.7, 19.6, 19.7, 19.8_
  - [~] 21.3 Fixture-level policy configuration
    - Seed `policy.stage_set`, period keys, OCR thresholds, band cutoffs, priority weights, promotion thresholds, monitoring thresholds, the label definition, and the citizen-visible event set as **synthetic-state fixture data** keyed to a synthetic state and act, so the point-in-time replay and training tests run against a self-contained configuration. This synthetic-state fixture is also the ONLY place any `retention.period.*` value is seeded: seed the DPDP_2023 Data_Category retention periods (Q10) here, keyed to the synthetic state, so the retention and erasure-path tests have configured periods to exercise without any retention period ever reaching the platform-wide baseline
    - Also seed the resolved platform-wide (state key `'*'`) default baseline from the requirements Q8 resolution as effective-dated seed/config rows: the RFCTLARR_2013 statutory periods (Q8) — notice periods, objection windows, and stage deadlines — each carrying a `# review-required before production use` comment. Seeding the statutory baseline platform-wide is safe because no irreversibility attaches to a statutory deadline: a wrong or unreviewed period surfaces as a visible breach flag or schedule an operator can correct, never as lost data. These are seed/config data, not product code — the AST lint of 2.6 and the schema guards of 2.7 still hold, so no period is a literal, a column default, or a CHECK constraint
    - Do NOT seed any `retention.period.*` row into the platform-wide baseline — the DPDP_2023 retention periods (Q10) live only in the synthetic-state fixture above, never platform-wide. Erasure requires BOTH `retention.sweep_enabled` true AND configured `retention.period.*` values, so leaving the periods unseeded outside fixtures means enabling the sweep alone erases nothing: an administrator must deliberately configure the reviewed periods for their state before any erasure can occur, which keeps irreversible erasure behind two independent deliberate actions rather than one. The decided DPDP default values remain recorded in the requirements Q10 resolution for that administrator to apply
    - Keep `retention.sweep_enabled` false — with no `retention.period.*` seeded outside the fixture, enabling the sweep alone would still erase nothing, and no erasure runs until a deployment confirms its state's land-record retention rules, configures its retention periods, and enables the sweep explicitly; seed no state-specific statutory rows either, so any state-and-act key with no effective value stays in the R28.5 refuse-and-report path for real deployments
    - _Requirements: 28.1, 28.5_

- [ ] 22. Machine learning pipeline (internal order matters; each sub-task depends on the one before)
  - [~] 22.1 ML table migrations
    - `ml_feature_row` with `reference_t`, `as_of_mode`, `feature_set_version`, `label_definition_version`, `features jsonb`, `consumed_event_ids bigint[]`, `content_hash`, `purpose`, and the uniqueness tuple; `ml_training_row`; `ml_model_version` including `feature_reference_bins` and `baseline_metrics`; `ml_prediction` with its idempotency unique constraint and history index; `ml_explanation_factor`; `ml_monitor_run`
    - _Requirements: 17.4, 18.6, 18.8, 18.16, 19.3, 19.10, 31.10_
  - [~] 22.2 `AsOfView` and the two as-of predicates
    - `ml/src/features/asof.py`: `build_as_of_view(session, case_id, t, mode)` fetching events ordered by `(occurrence_time, id)` with the mode's clause applied **in SQL**, then folding into a frozen `AsOfView` with stage history, notices, objections, parcels, awards, issues, documents, and `consumed_event_ids`. The fold is pure with no further I/O
    - A conventional feature table cannot satisfy R17.5 or R17.2 because it stores derived state rather than the evidence the state was derived from (§14.1); the stored `ml_feature_row` is a cache of a pure function's output, never a source of truth
    - _Requirements: 17.1, 17.2_
    - _Property 35_
  - [~] 22.3 `FeatureExtractor` protocol and the leakage guards
    - Complete the registry stubbed in 3.3: `name`, `source_attributes`, `compute(view, t)` — **no `Session`, no `Engine`, no connection in scope**, so an extractor that wants current state has nothing to ask
    - `no_database_access(session)` context manager registering a `before_cursor_execute` listener that raises `LeakageGuardViolation`, **active in production and not only in tests**, so a lazy load that sneaks in during a refactor raises on the first inference call rather than leaking quietly for six months
    - _Requirements: 17.1, 17.2, 17.3_
    - _Properties 35, 39_
  - [~] 22.4 `FeatureValue`, the extractor set, and `build_feature_row`
    - `FeatureValue` with a constructor invariant that exactly one of `value` and `missing_reason` is set, so an ambiguous value cannot exist; a legitimate zero and a missing value have different JSON, different storage, and different model input. **The Feature_Builder never imputes** — trees receive `NaN` plus a parallel `_is_missing` indicator so the model can learn from missingness
    - Elapsed-duration extractors as whole-day differences between T and the relevant event's occurrence time; count and state extractors over the view. Every extractor declares `source_attributes`, which is what powers both the label-disjointness and personal-data tests
    - `build_feature_row` performing all I/O in `build_as_of_view` and nothing after, inside `no_database_access`, returning `content_hash` over `(feature_set_version, as_of_mode, sorted(consumed_event_ids), canonical values)` — including the event id set makes the cache exactly invalidatable, so a backdated append that changes what is knowable at T makes the cached row detectably stale rather than plausibly correct
    - _Requirements: 17.4, 17.5, 17.6, 17.7_
    - _Properties 36, 38, 40_
  - [~] 22.5 Train/serve equality, tested three ways, in this task
    - `build_training_row` and `build_inference_row` as two deliberately identical entry points differing only in `purpose` on the persisted record; keeping two named entry points that provably agree is more honest than one function with a flag a future change could branch on
    - Hypothesis property test over arbitrary `(case, T)` asserting `content_hash` equality and canonical JSON equality
    - Hypothesis property test asserting a post-T append (later occurrence time, or later recording time) leaves the row's hash unchanged
    - **The nightly production re-derivation job** on the `ml` queue: take every `purpose='INFERENCE'` row written in the last 24 hours, rebuild through the training entry point, assert `content_hash` equality, and on divergence record an event and mark the model unmonitored. This is the test that matters — R17.8 is a claim about the deployed system and a CI property test on seeded fixtures cannot detect a real feature registry drifting from a real event log. It lands here with `build_feature_row`, not after the trainer
    - `test_label_and_feature_sources_are_disjoint` asserting the label function's declared sources and the union of extractor sources do not intersect
    - _Requirements: 17.3, 17.5, 17.8_
    - _Properties 35, 36, 37, 39_
  - [~] 22.6 `LabelDefinition`, `LabelOutcome`, and the pure label function
    - `ml/src/labelling/definition.py`: `LabelDefinition` carrying `formulation`, `stage_transitions_in_scope`, `deadline_baseline`, `baseline_fallback`, `horizon_days`, and `censoring` — **all four Q1-sensitive knobs are config fields, none is a literal**
    - `label_row(view, t, *, definition, deadline, now)` pure: no config lookup, no clock, no database, everything an argument, so it is exercised in a unit test with a synthetic timeline and no fixtures. `CENSORED` for `HORIZON_NOT_ELAPSED` and for `DEADLINE_BEYOND_HORIZON`
    - `LabelOutcome` populates `time_to_event_days` and `event_observed` **even in binary mode**, so a move to a survival formulation reads two fields that are already there and the labeller is untouched
    - `resolve_deadline` outside the label function reading `deadline_baseline`, so switching statutory-period to historical-percentile is one config value; labelling uses the `OCCURRED_BY` view because the outcome is a fact about the world and late recording does not change whether the case exited on time
    - `label_definition_version` travels on every row, and the trainer refuses a split containing more than one version, so a mixed-definition training set is detectable rather than silently averaged
    - _Requirements: 18.1, 18.2, 18.3, 18.4_
    - _Property 41_
  - [~] 22.7 `Model_Trainer`: splits, calibration, metrics, and the promotion gate
    - `ml/src/training/`: candidate reference points, labelling, censored exclusion from both splits with the count and rate recorded, temporal split where every eval `reference_t` is later than every train `reference_t`
    - Isotonic calibration so the reported probability is calibrated; AUPRC, AUROC, Brier, and ECE over 10 equal-width bins; PR-lift as `(auprc − eval_base_rate) / (1 − eval_base_rate)`; both base rates and both row counts reported beside every metric; the deadline-rule baseline metric set recorded alongside
    - `LABEL_BASE_RATE_SHIFT` event with both rates when they differ by more than 0.10, its id stated in the report; promotion gated on all four configured thresholds, otherwise `WITHHELD` with the report retained and a `MODEL_PROMOTION_WITHHELD` event
    - `quantile_bins(train_rows, n_bins=10)` stored at promotion — this is what makes drift monitoring possible without retaining raw training data, and keeps working after `MODEL_FEATURE` rows age out
    - Promotion records training window, feature set version, hyperparameters, metrics, both base rates, censored count and rate, and the promoting actor; gated on `model.administer`
    - _Requirements: 18.1, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10, 18.11, 18.12, 18.13, 18.14, 18.15, 18.16, 18.17, 31.12_
    - _Properties 42, 43, 44_
  - [~] 22.8 Trainer property tests and a calibration example test
    - Property test: no `CENSORED` row appears in either split, the temporal ordering holds, and the recorded censored count and rate equal a recount
    - Property test: each metric equals an independent reference computation, and PR-lift matches its formula
    - Property test: promotion happens exactly when all four thresholds are met, otherwise the report is retained and the withheld event exists; the base-rate-shift event and its report reference appear exactly when the rates differ by more than 0.10
    - Example test on the synthetic dataset that isotonic calibration measurably reduces ECE versus the uncalibrated estimator (R18.9 is a quality claim, not a property)
    - _Requirements: 18.5, 18.6, 18.7, 18.8, 18.9, 18.10, 18.11, 18.12, 18.13, 18.14, 18.15, 18.17_
    - _Properties 41, 42, 43, 44_
  - [~] 22.9 `Prediction_Service`: scoring, triggers, and failure handling
    - `score_case` on the `ml` queue triggered by an event whose type is in the feature registry's declared source set, plus the hourly stale sweep with a 24-hour age filter; idempotent by `UNIQUE (case_id, model_version_id, feature_row_id)`
    - Record probability, model version, feature set version, reference timestamp, and generation time; every generated probability retained
    - While no version is promoted, return **no** probability and omit the field entirely rather than nulling it, because a null could be read as "scored zero"; the portal renders not-scored
    - On failure retain the previous probability, set `risk_is_stale`, and append `SCORING_FAILED`; the portal shows the retained band with its original generation time and a stale marker
    - _Requirements: 18.18, 19.1, 19.2, 19.3, 19.10, 19.12_
    - _Properties 34, 48_
  - [~] 22.10 Banding, district cutoffs, and rebanding
    - `band_for(p, case, *, resolver)` returning `(band, cutoff_source, cutoff_set_version)`; `classify` is total and monotone because the config validator in 2.4 rejects any set that is not a contiguous partition of [0, 1] — guaranteed by validation rather than re-checked per call
    - District-specific cutoffs applied only where the district's count of `DELAYED`/`NOT_DELAYED` labelled cases is at or above the configured minimum; below it, platform cutoffs apply and a `DISTRICT_CUTOFFS_WITHHELD` event records the district, observed count, and minimum. `CENSORED` rows never contribute to that count
    - Reband pass triggered by 2.5 updating `risk_band` and `cutoff_set_version` on stored predictions while leaving `risk_probability` and `generated_at` untouched
    - Responses state whether the band came from district or platform cutoffs
    - _Requirements: 19.4, 19.5, 19.6, 19.7, 19.8, 19.9, 19.11_
    - _Properties 45, 46, 47_
  - [~] 22.11 Explanations, override recording, and the no-action guarantee
    - TreeSHAP factors persisted as ranked `ml_explanation_factor` rows with `label_key` resolved through the Localization_Service, so the plain-language label is translatable rather than an English string baked into the model artifact; top 5 presented with the model version and generation time
    - `POST /predictions/{case}/override` recording officer, overridden value, stated reason, and occurrence time, with the model output retained in the view alongside the override
    - Risk probability, band, explanation factors, and priority score excluded from every citizen response (enforced by the gate)
    - **Static test asserting `ml/src/` and `app/services/{prediction,priority,intervention}.py` import no mutating domain service**, so the intervention service cannot transition a stage, dispose an objection, or record a payout because it holds no reference to the code that can
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8_
    - _Properties 49, 50, 60_
  - [~] 22.12 `Model_Monitor`: calibration, drift, triggers, and the watchdog
    - Grouped by **the band assigned at prediction time** read from `ml_prediction.risk_band`, not the case's current band which may have been rebanded since; divergence as the absolute difference between realized rate and mean predicted; withheld with the observed count and reason below the configured minimum evaluable count
    - PSI over the stored 10 quantile edges with an `EPS` floor so an empty bin cannot make `ln()` infinite, plus an **11th bucket for the missing rate** — a feature that silently stops being derivable is one of the most likely real failure modes and binning only present values would hide it entirely
    - Three retraining paths each recording `RETRAINING_TRIGGERED` with the triggering condition and enqueueing one training run: calibration divergence, drifted feature count at or above the configured minimum within one computation, and model age reaching the configured maximum from `training_window_end`
    - `ml_monitor_run` inserted with `started_at` before work so a crashed run is visible as `RUNNING`; `check_watchdog` appending `MODEL_MONITORING_UNAVAILABLE` past 1.5× cadence and setting the state, which is joined into every response carrying a probability so the unmonitored label appears on the case where the score is being acted on
    - Supersession sets `promotion_state = 'SUPERSEDED'` and `superseded_by` and deletes nothing; `ml_prediction.model_version_id` has no cascade, so every historical score stays attributable
    - Notify officers holding `model.administer` on divergence and on drift
    - _Requirements: 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 31.7, 31.8, 31.9, 31.10, 31.11, 31.13, 31.14_
    - _Properties 74, 75, 76, 77, 78, 79_
  - [~] 22.13 Monitoring property tests
    - Property test: realized rate is computed per assigned-at-prediction band, divergence is the absolute difference, and the comparison is withheld with the observed count below the minimum
    - Property test: PSI equals the reference computation on the same edges, is zero for identical distributions, stays finite for disjoint supports, and accounts for the missing rate as a distinct bucket
    - Property test: each threshold breach produces the correctly-shaped event and notifies model administrators; each retraining condition triggers exactly once per detection
    - Property test: every superseded version remains retrievable with its report, both base rates, censored count, censoring rate, and feature set version; rebanding preserves probability, model version, and generation time
    - Property test: an unavailable monitoring state appears on every response presenting a probability for that version, with the last successful computation time
    - _Requirements: 19.9, 19.10, 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 31.7, 31.8, 31.9, 31.10, 31.11, 31.13_
    - _Properties 47, 74, 75, 76, 77, 78, 79_
  - [ ]* 22.14 Exploratory notebooks under `ml/notebooks/`
    - Label base-rate exploration, feature distribution review, calibration curve inspection. Genuinely optional: nothing in the pipeline, no property, and no `BLOCKING` path depends on them
    - _Requirements: none_
  - [ ]* 22.15 Per-district cutoff calibration tooling
    - An analysis job proposing district-specific cutoff values from that district's labelled history, for an administrator to review and write through `PUT /policy/{key}`. Optional because the **enforcement** of R19.6–19.8 lives in 22.10 and is covered by Property 46; only the value-proposing tool is discretionary
    - _Requirements: none beyond 19.6, 19.7 already covered in 22.10_

- [~] 23. Checkpoint — ML pipeline
  - Ensure all tests pass, ask the user if questions arise. Verify the nightly re-derivation job, the leakage guard, and the label/feature disjointness test all run against the synthetic dataset from task 21, and that a deliberately leaking extractor fails the build.

- [ ] 24. Priority score, intervention queue, and dashboard
  - [~] 24.1 `Priority_Engine`
    - `apps/api/app/services/priority.py`: weighted combination of risk, deadline pressure as remaining days normalised against the configured stage period, and case value normalised against the configured reference amount, all weights from config with `priority_weight_version` stored per score
    - Normalising by `weights.total()` keeps the output in [0, 100] for any non-negative weight set, which is why the validator in 2.4 only rejects negatives and an all-zero set; `pressure` clamps at 1 past the deadline where remaining days go negative, so the score is non-decreasing in both risk and pressure by construction
    - Recompute on a risk, deadline, or case-value change
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_
    - _Property 51_
  - [~] 24.2 Live intervention queue and recommended actions
    - Live indexed query over the `case_queue` partial index ordered by `priority_score DESC NULLS LAST` with `LIMIT/OFFSET` — at 10 000 cases this is an index-ordered scan of the first 50 rows, far inside 3 s, so no materialization is needed
    - Recommended actions attached only for the returned page, matched by the configured action rules against the denormalised counters and the deadline state, so attaching them costs no per-case queries
    - Disposition recording (accept, reject, defer) with officer and occurrence time, action retained retrievably
    - Response reports the **oldest** `priority_computed_at` on the page so an officer can see whether the ranking rests on scores that predate recent activity
    - Nightly reconciliation task recomputing the denormalised counters and recording a discrepancy event on any mismatch — denormalised counters nobody audits eventually lie
    - _Requirements: 21.7, 21.8, 21.9, 21.10_
    - _Properties 4, 31, 52_
  - [~] 24.3 Dashboard snapshot and per-metric timestamps
    - `dashboard_snapshot(area_code, metrics jsonb, computed_at)` and append-only `dashboard_band_history(area_code, month, band, case_count)`; `refresh_dashboard_snapshot` every 5 minutes on `maintenance` for each area holding a non-terminal case, computing each metric family in its own `try`
    - A request resolves the officer's scope to area codes and sums pre-aggregated counters — additive metrics roll up by summation, so one snapshot per leaf area serves every ancestor scope without a snapshot per role
    - **Per-metric** rather than per-snapshot timestamps, which is what makes R22.6 work: a failed metric is marked unavailable with its failure time while the rest is served
    - Drill-through builds its filtered list from the same predicate the metric counts, defined once in `app/services/dashboard/metrics.py`, so the list length equals the metric
    - _Requirements: 22.1, 22.3, 22.4, 22.6_
    - _Property 53_
  - [~] 24.4 Dashboard and queue UI
    - Stage distribution iterating the **resolved stage graph** rather than a fixed column list, so a state with four stages and a state with five both render without a branch; 12-month band trend from `dashboard_band_history`
    - Intervention queue view presenting Case_Reference, stage, risk band, remaining days, and priority score
    - _Requirements: 21.7, 22.1, 22.2, 22.3, 22.4_
    - _Property 53_
  - [~] 24.5 Priority, queue, and dashboard property and performance tests
    - Property test over degenerate and all-missing inputs: score in [0, 100], non-decreasing in risk with other inputs unchanged, non-decreasing as remaining days fall, recorded with its weight-set version
    - Property test: attached actions are exactly those the configured rules match, and dispositions are recorded and retained
    - Property test: every presented metric carries its computation time, a failing metric does not void its neighbours, and each metric's drill-through list length equals the metric
    - Nightly benchmarks in the §20.4 suite against a seeded 10 000-case district: queue p95 ≤ 3 s, dashboard p95 ≤ 3 s, case workspace p95 ≤ 3 s at 100 parcels and 200 documents, full validation evaluation p95 ≤ 5 s
    - _Requirements: 13.9, 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.8, 21.9, 21.10, 22.1, 22.3, 22.4, 22.5, 22.6, 23.6_
    - _Properties 51, 52, 53_
  - [ ]* 24.6 Monitoring dashboard surface beyond the required fields
    - Calibration-versus-realized charts, drift sparklines per feature, and retraining-trigger history views. Optional: R31.14's required presentation (realized rate and mean predicted per band from the most recent completed computation, with its time) ships in 22.12 and is covered by Property 74; this is the exploratory surface on top
    - _Requirements: none beyond 31.14 already covered in 22.12_
  - [ ]* 24.7 Officer chart polish
    - Animation, tooltip refinement, and responsive chart layout. The chart data shape and rendering that R22.2 requires ship in 24.4 with a shape test; this is presentation refinement only
    - _Requirements: none beyond 22.2 already covered in 24.4_

- [ ] 25. Retention, erasure, and data subject rights — sweep ships disabled
  - [~] 25.1 Retention schema and the erasure-date projection
    - `data_subject_request` migration with `due_at` materialized at receipt from the configured window so the overdue query is an index scan rather than a per-row policy resolution; `v_case_terminal` view; `retention_withholding` record for R32.14 gaps
    - The §6.2 erasure-date query resolving the period as of the **retention start date**, not today; a NULL result means withhold and record
    - `GET` returning, for any ownership record, its categories, the retention start date where determined, and the computed erasure date per category
    - _Requirements: 28.10, 32.1, 32.15_
    - _Property 66_
  - [~] 25.2 Complete `CATEGORY_MAP` and the metadata-walk test
    - Extend the registry created in 3.3 to every column of every table, including `Discriminated(on="field_name")` for `extracted_field.extracted_value` and `Reference(follows="data_category")` for `personal_datum.value_ciphertext`, with `NOT_PERSONAL` used explicitly rather than by omission
    - `test_every_column_is_classified` walking `Base.metadata.sorted_tables` and failing the build on any unclassified column. That is the whole mechanism for R32.2 holding over time rather than only on the day it was written
    - The same registry already drives the gate's field-coverage test (5.5), the feature disjointness test (3.3), and the DSAR field list (25.5)
    - _Requirements: 32.2_
    - _Property 80_
  - [~] 25.3 Two-armed erasure, disabled
    - `run_retention_sweep` per §17.2 returning immediately unless `retention.sweep_enabled` resolves true — **ships false, with no seeded `retention.period.*` rows**, so R32.14's withhold-and-record path is the operating state
    - Retention start is the occurrence time of the event that moved the case into a terminal stage; while the case is non-terminal the start is undetermined and erasure is withheld regardless of elapsed time
    - Restricted to the configured erasable set; a missing effective period records the withholding reason
    - One transaction per target: append `PERSONAL_DATA_ERASED` carrying entity id, attribute name, category, and erasure time; `UPDATE` the entity column to NULL; set `personal_datum.value_ciphertext = NULL` with `erased_at` and `erasure_event_id`. Idempotent by `WHERE erased_at IS NULL`
    - `due_for_erasure` is **generated from `CATEGORY_MAP`** — the sweep derives its column list rather than containing one, so a new personal-data column comes into scope automatically
    - `contact_mobile_hash` is `OWNER_CONTACT` and is erased with the plaintext, which means OTP login stops working for that owner. Correct given the retention period lapsed years after a terminal stage, but it should be an explicit expectation when Q10 is confirmed rather than a surprise
    - _Requirements: 32.3, 32.4, 32.10, 32.11, 32.12, 32.14_
    - _Properties 81, 82, 83_
  - [~] 25.4 Erasure property tests
    - Property test: every erased attribute is in an erasable category with a lapsed period, the event exists per erasure, and parcel identity and geometry, ownership share and validity, award and payout amounts, and every event row are bit-identical to their pre-erasure snapshot
    - Property test: every stored event row is byte-identical before and after, and the erasure is represented solely by one newly appended compensating event
    - Property test: the erased value is absent from every returned payload while actor, entity id, both timestamps, and position in the ordering are identical to what was returned before
    - Property test: a non-terminal case has an undetermined retention start and nothing is erased regardless of elapsed time
    - Property test: the computed erasure date uses the period effective at the retention start, not the current period
    - _Requirements: 28.10, 32.3, 32.4, 32.10, 32.11, 32.12, 32.13, 32.15_
    - _Properties 66, 81, 82, 83, 84_
  - [~] 25.5 DSAR access and correction handlers
    - `GET /c/my-data` assembling the response by **iterating `CATEGORY_MAP`** for personal-data attributes on the requester's own records so it cannot fall behind the schema; the government identifier masked under R26.5, with a `DATA_ACCESS_REQUEST_SERVED` event. **Q10 asks whether a DSAR response may carry it unmasked** — this design masks it until Q10 says otherwise, and unmasking is one change to the gate's `PERMISSION` visibility
    - `POST /c/correction` writing **only** to `data_subject_request`: target attribute, current value, asserted value, receipt time; routed to officers whose scope contains the case
    - `GET /dsar` and `POST /dsar/{id}/disposal` gated on `dsar.dispose`, recording outcome, reasons, deciding officer, and disposal time with a `CORRECTION_REQUEST_DISPOSED` event
    - Receipt and completion times recorded; a daily task flags requests past `due_at` without a completion time
    - **Static test asserting `app/citizen/` imports no versioned repository and no entity-mutating service**, so no citizen-submitted value can reach stored state; a change reaches state only through an officer modification under R6 or R12 with its own event and version check
    - _Requirements: 32.5, 32.6, 32.7, 32.8, 32.9_
    - _Properties 61, 85, 86_
  - [~] 25.6 DSAR property tests
    - Property test: for any correction request carrying any asserted value, the targeted attribute is unchanged until an officer modification is recorded, and the request records all four fields and routes to exactly the in-scope officers
    - Property test: receipt and completion times are recorded, overdue requests are flagged against the configured window, and a correction disposal records outcome, reasons, officer, and time
    - _Requirements: 32.6, 32.7, 32.8, 32.9_
    - _Properties 85, 86_

- [ ] 26. Bulk import
  - [~] 26.1 `import_batch` and `import_row` migrations
    - `import_row (batch_id, ordinal)` primary key with `state`, `committed_entity_id`, `rejection jsonb`, and the `import_row_pending` partial index; `import_batch` with `last_processed_ordinal`, `state`, submitted count, and content checksum
    - `IMPORT_BATCH_CREATED` event; submission gated on `import.submit`
    - _Requirements: 30.1, 30.2, 30.7_
  - [~] 26.2 Chunked set-based `process_import_chunk`
    - `CHUNK = 1000` per §16.2: one query per lookup kind for the whole chunk into a `ChunkRuleContext`, the **same rule functions** as manual entry evaluated in memory, bulk entity insert with `RETURNING`, bulk event insert with `provenance='IMPORTED'` and the batch id, and row-state updates all in one transaction
    - `ctx.observe(r)` after each passing row so intra-batch duplicates are caught without a query — a lookup issued before the chunk started cannot know about a survey number appearing twice inside it
    - Constraint trigger disabled for the chunk via the session flag from 3.7, with the invariant asserted **set-wise** in one query before commit instead of 1000 trigger firings; same guarantee, and the tradeoff is deliberate because this is one function written once
    - Documents routed through `Document_Service.store()` so the content-type restriction, size limit, duplicate checksum rejection, checksum recording, and extraction enqueue are the same code
    - Pre-partition the batch by parcel key so one parcel's owners land in one chunk; where owners arrive across batches the share-sum rule is **not** evaluated at import time and runs post-commit in the Validation_Engine as a `BLOCKING` issue, because a partial owner set is an incomplete parcel rather than a failing row and rejecting it would make a two-batch migration impossible
    - _Requirements: 30.2, 30.3, 30.4, 30.5, 30.8, 30.9, 30.10_
    - _Properties 12, 20, 71, 72, 73_
  - [~] 26.3 Batch report, interruption, and resumption
    - Report stating submitted, committed, and rejected counts and every rejected-row entry with failing rule id, offending attribute, observed value, and matching identifier where applicable; `IMPORT_BATCH_COMPLETED` event; `submitted = committed + rejected` asserted at completion
    - Exactly-once without distributed transactions: the entity insert and the `state = 'COMMITTED'` update share one transaction, so resumption is `WHERE state = 'PENDING' ORDER BY ordinal` and an already-committed row is structurally unreachable; a redelivered chunk finds nothing pending and exits
    - `INTERRUPTED` state with `last_processed_ordinal`; report and rejected-row entries retained retrievably
    - _Requirements: 30.6, 30.7, 30.12_
    - _Property 73_
  - [~] 26.4 Import batch view
    - `GET /imports/{id}` presenting batch state, the three counts, and rejected-row entries filterable by failing rule identifier
    - _Requirements: 30.13_
    - _Property 72_
  - [~] 26.5 Import property tests and throughput benchmark
    - Property test submitting the same generated row through both the import path and the manual path and asserting identical issue sets — this is what stops the two validation paths drifting apart
    - Property test over any interleaving of passing and failing rows: committed set equals the passing set exactly, no failing row withholds a passing row, each rejection carries rule id, attribute, and observed value, and the counts reconcile
    - Property test: every committed row has an `IMPORTED`-provenance event with the batch id, and for any interruption at any ordinal followed by resumption the final committed multiset equals the passing set with nothing committed twice
    - Nightly throughput benchmark asserting at least 10 000 parcel rows per minute at p95 over the trailing 10 batches of at least 10 000 rows
    - _Requirements: 30.1, 30.2, 30.3, 30.4, 30.5, 30.6, 30.7, 30.8, 30.9, 30.11, 30.12, 30.13_
    - _Properties 12, 71, 72, 73_

- [ ] 27. Localization
  - [~] 27.1 `Localization_Service` and catalogs
    - `apps/api/app/services/localization.py` resolving keys from flat per-locale JSON catalogs; server-side resolution for the citizen portal means **no i18n bundle is transferred**, a direct contribution to R24.1's budget
    - Language selection persisted for the citizen session, applying to strings, dates, numbers, and currency
    - Fallback to the deployment default with the missing key recorded to `missing_translation(key, locale, first_seen_at, occurrence_count)` rather than logged, so the gap is queryable and fixable rather than buried in log volume
    - Coverage test asserting every citizen-facing and officer-facing key resolves in every configured language
    - _Requirements: 27.1, 27.2, 27.3, 27.4_
    - _Property 63_
  - [~] 27.2 Script round-trip integrity
    - **No unicode normalisation on write.** Storing NFC when the input was NFD would make a read-back differ from the value written, which R27.5 forbids in as many words. UTF-8 encoding, `text` columns, no collation-based folding on the identity index
    - The consequence is that two village names differing only in normalisation form are distinct strings and would evade duplicate detection; resolved by the `village_norm` generated column from 9.1, used for matching only and never for display or export
    - Property test over `st_devanagari_text()` including combining marks, both normalisation forms, and ZWJ: the value read back equals the value written character for character, and the rendered and exported value equals the stored value
    - _Requirements: 27.5_
    - _Property 62_
  - [~] 27.3 Stage and event label keys
    - `label_key` pointers on stage-set entries and citizen-visible event types resolved through the service, so onboarding a state with a different stage set is `INSERT`s plus localization keys and no code change (§4.4)
    - _Requirements: 27.1, 27.2_
    - _Property 63_

- [ ] 28. Measurement harnesses for the requirements §2 flags as not satisfiable as written
  - [~] 28.1 R24.3 throttled-network p95 harness under the stated warm-connection reading
    - Playwright + CDP `Network.emulateNetworkConditions` at 400 kbps down, 400 kbps up, 2000 ms latency; 100 cold loads with an empty HTTP cache and empty Cache Storage; assert FCP p95 ≤ 5 s and interactivity p95 ≤ 8 s
    - **The harness records whether DNS and connection setup were inside the measurement**, so the result is interpretable against the ambiguity rather than a bare pass/fail. Under the proposed reading — DNS resolved, reusable connection or HTTP/3 0-RTT, empty HTTP cache — the target is met with margin. Under the strictest reading, DNS + TCP + TLS at 2000 ms RTT is 6 s before the request is even sent, so FCP cannot be under 5 s by any architecture and the requirement needs a different number
    - Nightly, not per-PR: 100 loads at ~8 s each is 15–25 minutes
    - _Requirements: 24.3_
  - [~] 28.2 R15.8 geometry simplification made explicit in the contract
    - The simplification implemented in 17.2; this sub-task adds the response-level declaration of tolerance and coordinate precision, the payload-size assertion at 5000 parcels, and the documentation that full-fidelity geometry is a separate single-parcel endpoint. Without the simplification the requirement is unachievable: 5000 cadastral polygons at ~40 vertices are ~5 MB of GeoJSON and over 8 s of transfer at 5 Mbps
    - _Requirements: 15.4, 15.8_
  - [~] 28.3 R11.8 measured OCR latency distribution
    - Record and report the p95 of extraction time from job dequeue over the trailing 100 completed jobs for single-page documents up to 2 MB, so the claim is evidenced rather than assumed
    - The recognizer stays behind the `Recognizer` protocol from 16.2 so CPU-versus-GPU is a deployment choice. **Selecting the hardware is a precondition, not a task**: CPU Tesseract with Devanagari runs 8–25 s and clears 60 s; a transformer recognizer will not clear it on CPU
    - _Requirements: 11.8_
  - [~] 28.4 R27.6 font cap as a build-step failure
    - The build step from 19.6 that fails when a produced subset exceeds 40 KB compressed, plus the CI assertion in 19.5 over every configured language. Where a deployment's confirmed Q7 script has no viable subset and weak device coverage, R27.6 and R24.1 conflict and the build failure is the signal to revisit the numbers rather than ship an oversized file
    - _Requirements: 24.1, 27.6_

- [~] 29. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise. Confirm every guard is green and fails on deliberate violation: the AST lint, the three schema guards, the route-table and field-coverage tests, the RBAC matrix, the metadata-walk classification test, the feature/personal-data disjointness test, the label/feature disjointness test, the no-mutating-import test for `ml/src` and `app/citizen/`, the same-version race harness, the citizen transfer budget, and the nightly re-derivation job. Confirm no statutory period, retention period, or label definition value is seeded outside test fixtures.

## Notes

- **Test sub-tasks are not marked optional here.** The workflow's default is to mark them with `*`, but 88 of this design's correctness properties are the specification of behaviour rather than extra assurance, and several structural tests (the AST lint, the route-table test, the field-coverage test, the metadata-walk test, the disjointness tests) are the *only* thing preventing a whole class of silent defect. Skipping them does not produce a faster MVP, it produces a system whose central claims are unverified.
- **Four tasks are marked optional** (`22.14`, `22.15`, `24.6`, `24.7`): exploratory notebooks, per-district cutoff *calibration tooling*, the monitoring dashboard surface beyond R31.14's required fields, and officer chart polish. In each case the requirement-bearing and property-bearing behaviour ships in a required task and only the discretionary surface is optional. Nothing a correctness property or a `BLOCKING` validation path depends on is marked optional.
- **One deliberate divergence from the task-list brief.** The brief lists a `daterange` exclusion constraint among the migration work. §6.1 explicitly rejects an exclusion constraint on `(parcel_id, owner_identity_key, validity)`: R13.5 requires an overlapping same-owner validity period to *raise a Validation_Issue*, and an exclusion constraint would reject the write instead, contradicting the requirement and breaking the import's partial-commit semantics. Task 9.1 creates the `daterange` generated column and the GiST index, and no exclusion constraint.
- **The brief refers to four requirements flagged in §2; §2 names three** (R24.3, R15.8, R11.8). Task 28 covers those three plus the R27.6 font conflict flagged in §10.4, which is the same kind of finding — a stated number that may not survive a particular deployment.
- **Q11 (proactive citizen notification) is resolved as out of scope**, so there is no notification task and its absence is a recorded decision rather than an oversight. The Citizen_Portal is pull-only: a citizen learns of a stage change by opening it, which is what R25.1's next-expected-step presentation is for. The only outbound message BHUMISETU sends is R3.1's one-time passcode, built in task 7.4. If Q11 is later confirmed as in scope, it arrives as a new requirement with its own trigger event set, channel, consent record, language-selection rule, and delivery-failure behaviour, and as new tasks — it is not latent in any task listed here.
- Preconditions requiring a human decision or hardware are named inside the tasks that depend on them rather than made into tasks: confirming Q1, Q8, and Q10; hand-labelling the Holdout_Set; choosing the OCR recognizer's hardware target; confirming the R24.3 measurement reading; and confirming whether a DSAR response may carry an unmasked government identifier.
- Each task references the specific acceptance criteria it implements, and property-bearing tasks cite the design's property numbers, so the coverage table below can be checked against the requirements document criterion by criterion.
- **The dependency graph serializes every migration-bearing task into its own wave.** Alembic revisions are separate files but share one linear `down_revision` chain, so two migration tasks running in parallel produce a branched history that has to be merged by hand. This is why the graph is 30 waves rather than a dozen: the 22 tasks that add schema are the critical path, and the code and test tasks fan out around them.

## Requirement Coverage

Each row lists every required sub-task whose `_Requirements:` line cites at least one criterion of that requirement, in task order. Optional sub-tasks are not listed: `22.14`, `22.15`, `24.6`, and `24.7` state "none" or "none beyond … already covered in" a required task, so they carry no coverage of their own.

| Req | Tasks |
|---|---|
| 1 Officer auth | 7.1, 7.2, 7.3, 7.6 |
| 2 RBAC and scope | 1.2, 2.5, 5.1, 5.3, 5.6, 8.3, 8.4 |
| 3 Citizen access | 5.1, 7.2, 7.4, 7.5, 7.6 |
| 4 Event log | 1.1, 3.1, 3.2, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 21.1 |
| 5 Project and case | 2.3, 8.1, 8.2, 8.4 |
| 6 Parcel and ownership | 9.1, 9.2, 9.3, 9.4, 13.3, 13.6 |
| 7 Notices and deadlines | 2.2, 2.3, 2.6, 2.7, 10.1, 10.2, 10.3, 10.4 |
| 8 Objections | 11.1, 11.2 |
| 9 Award and payout | 12.1, 12.2, 12.3, 13.3, 13.6 |
| 10 Documents | 3.8, 15.1, 15.2, 15.3, 15.4 |
| 11 OCR and accuracy | 1.3, 15.3, 16.1, 16.2, 16.3, 16.4, 16.6, 16.7, 16.8, 18.5, 28.3 |
| 12 Confidence routing | 16.1, 16.4, 16.5, 16.8, 18.3 |
| 13 Validation execution | 13.1, 13.2, 13.3, 13.4, 13.6, 24.5 |
| 14 Severity and audit | 5.6, 8.2, 8.4, 13.1, 13.2, 13.4, 13.5, 13.6, 18.5 |
| 15 Geometry | 10.1, 17.1, 17.2, 17.4, 17.5, 17.6, 28.2 |
| 16 Map | 17.3, 17.6, 18.2, 18.4, 18.7 |
| 17 Point-in-time features | 3.3, 21.1, 22.1, 22.2, 22.3, 22.4, 22.5 |
| 18 Training and promotion | 18.2, 21.2, 22.1, 22.6, 22.7, 22.8, 22.9 |
| 19 Risk scoring and bands | 18.2, 21.2, 22.1, 22.9, 22.10, 22.13 |
| 20 Explanation and HITL | 22.11 |
| 21 Priority and queue | 24.1, 24.2, 24.4, 24.5 |
| 22 Dashboard | 24.3, 24.4, 24.5 |
| 23 Case workspace | 8.3, 18.2, 18.3, 18.5, 24.5 |
| 24 Citizen budget | 1.3, 19.1, 19.3, 19.4, 19.5, 19.7, 28.1, 28.4 |
| 25 Citizen content | 15.2, 19.1, 19.2, 19.3, 19.7 |
| 26 Citizen redaction | 5.2, 5.3, 5.4, 5.5, 19.3, 19.7 |
| 27 Localization | 1.3, 18.6, 19.1, 19.5, 19.6, 27.1, 27.2, 27.3, 28.4 |
| 28 Policy config | 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 2.8, 10.4, 13.2, 16.7, 21.3, 25.1, 25.4 |
| 29 Concurrency | 4.1–4.5, 8.2, 16.5, 18.1 |
| 30 Bulk import | 13.2, 15.1, 15.4, 26.1–26.5 |
| 31 Model monitoring | 5.6, 18.2, 22.1, 22.7, 22.12, 22.13 |
| 32 Retention and DSAR | 3.2, 3.3, 3.5, 25.1–25.6 |

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0,  "tasks": ["1.1", "1.3"] },
    { "id": 1,  "tasks": ["1.2", "1.4", "3.3"] },
    { "id": 2,  "tasks": ["2.1"] },
    { "id": 3,  "tasks": ["3.1", "2.2", "2.3", "2.4"] },
    { "id": 4,  "tasks": ["3.2", "2.5", "2.6", "2.7"] },
    { "id": 5,  "tasks": ["3.8", "2.8", "3.4"] },
    { "id": 6,  "tasks": ["4.1", "3.5", "3.6", "5.1"] },
    { "id": 7,  "tasks": ["8.1", "4.2", "5.2"] },
    { "id": 8,  "tasks": ["9.1", "4.3", "5.3"] },
    { "id": 9,  "tasks": ["10.1", "4.4", "4.5", "5.4", "5.5", "5.6"] },
    { "id": 10, "tasks": ["11.1", "7.1", "7.2", "8.2"] },
    { "id": 11, "tasks": ["12.1", "7.3", "7.4", "8.3", "9.2"] },
    { "id": 12, "tasks": ["13.1", "7.5", "9.3", "10.2", "11.2"] },
    { "id": 13, "tasks": ["15.1", "7.6", "8.4", "9.4", "10.3", "12.2", "13.2"] },
    { "id": 14, "tasks": ["16.1", "10.4", "12.3", "13.3", "15.2", "17.1"] },
    { "id": 15, "tasks": ["16.6", "13.4", "15.3", "15.4", "16.2", "17.2", "17.4"] },
    { "id": 16, "tasks": ["16.7", "13.5", "16.3", "17.3", "17.5"] },
    { "id": 17, "tasks": ["3.7", "13.6", "16.4", "17.6", "21.1"] },
    { "id": 18, "tasks": ["27.1", "3.9", "16.5", "21.2", "21.3"] },
    { "id": 19, "tasks": ["22.1", "16.8", "27.2", "27.3", "18.1"] },
    { "id": 20, "tasks": ["24.3", "22.2", "18.2", "18.3"] },
    { "id": 21, "tasks": ["25.1", "22.3", "18.4", "18.5", "19.1"] },
    { "id": 22, "tasks": ["26.1", "22.4", "18.6", "19.2", "19.4"] },
    { "id": 23, "tasks": ["22.5", "22.6", "18.7", "19.3", "19.6", "26.2"] },
    { "id": 24, "tasks": ["22.7", "19.5", "19.7", "26.3", "25.2"] },
    { "id": 25, "tasks": ["22.8", "22.9", "26.4", "25.3", "28.1"] },
    { "id": 26, "tasks": ["22.10", "22.11", "24.1", "26.5", "25.4"] },
    { "id": 27, "tasks": ["22.12", "24.2", "25.5", "28.2", "28.3"] },
    { "id": 28, "tasks": ["22.13", "22.14", "24.4", "25.6", "28.4"] },
    { "id": 29, "tasks": ["22.15", "24.5", "24.6", "24.7"] }
  ]
}
```
