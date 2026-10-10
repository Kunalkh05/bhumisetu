# Deployment notes

Provider choices are hypotheses until verified against the actual repo and account.
Possible topology: Vercel frontend; compatible Docker/Python API host; persistent Celery worker; managed PostgreSQL with verified PostGIS support; managed Redis; private object storage if required.

Never commit credentials. Do not create paid resources or run migrations without explicit approval. Confirm pricing, sleep/worker behavior, storage persistence, backups, PostGIS, and model artifact access before selecting providers.
