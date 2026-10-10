# BHUMISETU Autonomous Deployment Harness

Portable executable harness for the existing BHUMISETU repository. It combines repository preflight, an Antigravity adapter, build/test checks, frozen-ML artifact hash checks, opt-in deployment commands, HTTPS smoke tests, and reports.

## Install
1. Unzip this bundle.
2. Copy `bhumisetu_deployment_harness/` into the root of your existing BHUMISETU repository.
3. Run `./bhumisetu_deployment_harness/run.sh preflight`.
4. Review `reports/` and the current Git diff.
5. Configure `adapters/antigravity_adapter.sh` for the documented invocation of the Antigravity CLI installed on your machine. The adapter receives the task on stdin. It intentionally does not guess CLI flags.
6. Run `./bhumisetu_deployment_harness/run.sh agent`, then `validate`.
7. Configure provider commands in `.env.harness` only after reviewing them and any costs. Set `ALLOW_INFRA_CHANGES=1` only when you explicitly authorize deployment.
8. Run `deploy`, then configure `FRONTEND_URL` and `BACKEND_URL` and run `smoke`.

## Commands
`preflight | agent | validate | deploy | smoke | all-safe | report`

## Safety
- Does not retrain models or intentionally modify model artifacts.
- Hashes tracked candidate ML/model files before and after validation; changes are reported as failure.
- Does not reset/migrate databases automatically.
- Does not print env file values.
- Cloud deployment commands are disabled unless `ALLOW_INFRA_CHANGES=1`.
- Does not claim success unless actual URL smoke tests pass.
- Provider compatibility and costs must be verified against your repository and accounts.
- Add `bhumisetu_deployment_harness/.env.harness`, `reports/`, and `.state/` to the root `.gitignore`.
