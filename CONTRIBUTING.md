# Contributing to BHUMISETU

## How work happens here

This project is spec-driven. Three documents under `.kiro/specs/bhumisetu/` are
written and agreed before code:

- **`requirements.md`** — what the system must do, as testable acceptance
  criteria. Every criterion is numbered (`R14.3` means requirement 14,
  criterion 3).
- **`design.md`** — how it is built, plus 88 numbered correctness properties.
- **`tasks.md`** — the implementation plan, in dependency order.

Code traces back to all three. A pull request that implements behaviour nobody
wrote down is harder to review than one that cites `R14.3`, because the reviewer
has no standard to check it against.

If you think a requirement is wrong, change the requirement in its own commit and
say why. Do not quietly implement something different — the spec is how the rest
of us know what the system is supposed to do.

## Picking something up

1. Open [`tasks.md`](.kiro/specs/bhumisetu/tasks.md). Unchecked boxes are open.
2. Check the **Task Dependency Graph** at the bottom. Tasks are grouped in waves;
   a task whose wave has unfinished predecessors is not ready, and starting it
   means building on an interface that does not exist yet.
3. Read the requirements the task cites, and the design sections it links.
4. Claim it by opening an issue or saying so, then branch.

Tasks marked `[ ]*` are optional — notebooks, chart polish, calibration tooling.
Nothing a correctness property depends on is optional.

## Four mechanisms to understand first

Almost every file in the backend touches at least one of these. Reading them
first will save you re-doing your first pull request.

**`PolicyResolver`** (design §4) — every statutory period, threshold, cutoff, and
weight resolves through it, keyed by state, act, and effective date. It has no
`default=` parameter, on purpose: a default is how a legal deadline ends up
hardcoded. If a value is missing the operation refuses and reports the missing
key. A CI lint fails the build if an integer literal reaches date arithmetic.

**The event log** (design §5) — append-only, enforced by a revoked database
grant rather than by application code. Event payloads never store personal data
inline; they hold `{"$pd": id}` references into a separate table, which is what
lets a name be erased later without touching a stored event. Two different as-of
predicates exist and they are not interchangeable: `KNOWABLE_AT` filters on both
occurrence and recording time and is for ML features; `OCCURRED_BY` filters on
occurrence time alone and is for timelines.

**`VersionedRepository`** (design §7) — the only write path for a versioned
entity. The conditional `UPDATE ... WHERE entity_version = :expected` runs
*before* the event insert, in the same transaction, so a rejected write appends
no event structurally rather than by relying on rollback. Do not write an
`UPDATE` against a versioned table from anywhere else; a static test will fail
you.

**`GatedRoute` / `ResponseGate`** (design §8) — every response passes through one
serialization gate that omits fields the caller may not see. A redacted field is
*absent from the JSON*, not null and not merely unrendered. Two tests keep this
honest: one asserts every route is a `GatedRoute`, another intersects every
response model's fields against the personal-data registry and fails on an
unannotated match. Adding `contact_mobile` to a model without annotating it
breaks the build.

## Conventions

**Commits** — see [`docs/commit-convention.md`](docs/commit-convention.md). Small
and single-purpose, `type(scope): description`, citing requirements in the body.

**Tests** — write them in the same commit as the behaviour. The design defines 88
correctness properties; they are the specification of behaviour, not extra
assurance. Property tests use Hypothesis with a persistent example database, so a
shrunk counterexample replays on every later run.

**Numbers need a measurement method.** "Fast" is not a requirement. Every
performance claim in the spec has a percentile, a sample basis, and a benchmark.
If you add one, add its benchmark too.

**No legal number in code.** Not in a literal, not in a column default, not in a
CHECK constraint. Configuration only.

## What is deliberately not finished

Three policy decisions are open, and code depends on them staying open rather
than being guessed:

- **Q1** — what counts as "delayed". The whole ML label depends on it. Labelling
  is a config-driven function so changing it is a config change and a retrain.
- **Q8** — the governing act and its statutory periods. **No period values are
  seeded.** The platform refuses dependent operations and reports the missing key.
  This is the intended state, not a bug.
- **Q10** — personal data retention periods. **Erasure ships disabled** with no
  seeded periods. Erasure is irreversible, so confirming late costs nothing while
  confirming wrongly is unrecoverable.

If you hit a `POLICY_VALUE_MISSING` response, that is the system working. Supply
the value as a test fixture; do not seed it as real data.

## Pull requests

- One concern per pull request. A branch that fixes a bug and refactors around it
  is two reviews wearing one hat.
- Say which task and requirements it implements.
- Include the test output. If a benchmark moved, say by how much.
- Say what you could not verify. A pull request that admits an untested path is
  more useful than one that implies everything was checked.

## Getting set up

[`docs/local-setup.md`](docs/local-setup.md). There is a Docker path and a
no-Docker path; both are supported.
