# Deployment review

[Review index](README.md) · [Original deployment](../../superpowers/specs/core-practice-loop/11-deployment.md)

## O1 — P2: size the full host, not only the web process

The draft combines two workers capped at 512 MB each with a roughly $5 instance.
A per-worker virtual-memory limit is neither measured resident usage nor total host RAM.
Measure the app, SymPy workers, Caddy and operating system together under concurrency.
Start with one worker and bounded queue; select a host after that measurement.
AWS lists different IPv4 and IPv6-only bundles; verify region, RAM and networking
before quoting a monthly total. [Lightsail pricing](https://aws.amazon.com/lightsail/pricing/)

An AWS Budget notification is not a hard spending limit and can arrive after usage.
[AWS budget documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
Set an application LLM request/token budget and provider limits in addition to alerts.
Record hosting, storage, domain and model usage as separate cost components.

## O2 — P2: deploy an identified, tested release

Build once, test, push an immutable image reference and deploy that exact digest.
The deploy workflow must depend on successful CI for the same commit.
Keep a known-good previous image and document rollback plus schema compatibility.
Run migrations once per deployment; do not race them across app replicas.
Use health/readiness checks and a real container request test, not Dockerfile string checks.
Confirm Compose volume paths, non-root write permissions and SQLite WAL behavior.

## O3 — P2: a backup needs a restore exercise

Use SQLite's supported online backup mechanism, then upload the completed snapshot.
Keep backup files private and encrypted with narrowly scoped storage access.
Document required sqlite3/AWS CLI tools, paths, scheduling and failure alerts.
Before automated retention removes any backup, scope it to this application's prefix.
Periodically restore into a new database and confirm schema, users and attempts.
A text check for “14 backups” cannot establish correct retention or recoverability.

## O4 — MVP operating contract

Use one application process initially; in-memory rate limits are per process.
Bound request size, verifier queue, model timeout, retries and per-user usage.
Log request IDs, status, duration, model usage and verification outcome without secrets.
Persist source/content/model versions so errors can be reproduced.
Add a small seeded demo so reviewers can explore without waiting for a content pipeline.
Keep real pilot accounts separate from the disposable demo data.

## O5 — order the work around integration

Move minimal container/HTTPS deployment alongside the first working endpoint.
Move real MathLive capture and a tiny content fixture before the verifier interface freezes.
Move session state/transaction design before repositories and recommendation code.
Add the first browser smoke test when the first answer form works, then expand it.
Do not wait until Task 18 to discover that the frontend payload and backend disagree.
