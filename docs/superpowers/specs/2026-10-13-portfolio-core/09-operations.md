# 09 — Operations

[Contracts index](README.md) · [Operations review](../../../reviews/2026-10-13/operations.md)

## Host sizing (measure first)

- **Milestone A:** deploy the skeleton on the smallest Lightsail bundle that has ≥ 1 GB RAM. The region, bundle, RAM and IPv4/IPv6 option are recorded in `docs/ops/host.md` **with the price on the date checked**.
- **Milestone B:** measure resident memory for the app, a verifier worker under the heaviest case in the evaluation set, Caddy and the OS. The measurement runs under 16 concurrent submits. Set the pool size and `RLIMIT_AS` from those numbers, and re-pick the bundle only if the measurements require it.

## Release identity

- **CI** builds the image **once**, runs the tests against that image (container-level `/readyz` plus one real submit), and pushes it to GHCR **by digest**.
- **Deploy** runs only after CI succeeds **on the same commit**. It deploys that exact digest.
- **Rollback:** the previous digest is recorded on the host (`deploy/last-good`). Rolling back is `deploy/rollback.sh`, documented in `docs/ops/runbook.md`.
- **Migrations:**
  - run once per deploy as a separate `alembic upgrade head` step, before the app starts
  - must stay backwards-compatible for one release, so a rollback never meets an incompatible schema
- **Single app process** (see the rate-limit assumption in [07](07-application-and-web.md)).
- **Volumes:**
  - SQLite stays in WAL mode on a host volume owned by the non-root container user.
  - Permissions are checked by a container test.

## Backups and restore

- **Nightly:** SQLite's online backup API (`sqlite3 .backup`) writes a complete snapshot. It is then uploaded to a private, server-side-encrypted S3 bucket under the prefix `mathtutor/<env>/`.
- **Retention** applies only within that prefix, keeping 14 snapshots. A failure sends an alert email via cron's `MAILTO` or a webhook.
- **Restore drill** (milestone D, then monthly): restore the newest backup into a fresh database, run migrations, and check the user, session and attempt counts against production. The drill is logged in `docs/ops/restore-log.md`.
- **IAM:** a dedicated user limited to `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` and `s3:DeleteObject` on that prefix.

## Costs

- **Tracked separately:** hosting, storage, domain and (from milestone C) LLM usage.
- **An AWS Budget alert is a notification, not a cap.** It is configured, and the README says it isn't a cap.
- **LLM spending** (milestone C) is bounded inside the app by per-user and global daily token caps, a request timeout and a retry limit, together with provider-side limits.

## Demo data

- A disposable demo account with seeded history lets reviewers try the app.
- It's kept separate from any real pilot accounts and reset nightly.
