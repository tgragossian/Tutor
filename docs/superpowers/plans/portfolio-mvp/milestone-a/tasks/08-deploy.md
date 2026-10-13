# Task 8: Deploy the skeleton to Lightsail

[Milestone A plan](../README.md) · [Spec 09](../../../../specs/2026-10-13-portfolio-core/09-operations.md)

Most steps here are run by **Thomas**, because they create accounts, cost money or change DNS. The agent writes the scripts and docs, and checks the result from outside.

**Files:**
- Create:
  - `deploy/bootstrap.sh`
  - `docs/ops/host.md`, `docs/ops/runbook.md`
- Modify:
  - `docs/ops/README.md`: link both new docs
  - `README.md`: add the live URL and a "Status: milestone A skeleton" line

**Interfaces:**
- Consumes: `deploy/compose.yaml`, `deploy/Caddyfile` and `deploy/.env.example` from task 7.
- Produces: a public HTTPS endpoint, recorded in `host.md`. Milestone B deploys to the same host.

**`bootstrap.sh`** (Ubuntu 24.04 LTS, idempotent, `set -euo pipefail`):
- Installs Docker Engine and the compose plugin from Docker's apt repository.
- Enables unattended security upgrades.
- Creates `/srv/mathtutor`.
- Prints the next manual steps. It never writes secrets.

- [ ] **Step 1 (Thomas): Budget alert.**
  - Create an AWS Budget with a **$10/month alert** to your email.
  - It's a notification, not a cap. Record that in `host.md`.
- [ ] **Step 2 (Thomas): Create the Lightsail instance.**
  - Ubuntu 24.04, on the smallest bundle with **at least 1 GB RAM**.
  - Attach a static IP.
  - Firewall: allow 22 from your IP only, and 80 and 443 from anywhere.
  - Record the region, bundle, RAM, IPv4/IPv6 option and **monthly price with the date checked** in `host.md`.
- [ ] **Step 3 (Thomas): Domain.**
  - Use a domain or subdomain you control, and point an `A` record (and `AAAA` if you use IPv6) at the static IP.
  - Record the registrar and yearly cost. Don't record any credentials.
- [ ] **Step 4 (Thomas): Set up the host.**
  1. Copy over and run `bootstrap.sh`.
  2. `git clone` the repository into `/srv/mathtutor`. A public repository can be cloned over HTTPS; a private one needs a read-only deploy key.
  3. Create `deploy/.env` **on the host only**:
     - `SITE_ADDRESS=<domain>`
     - `MATHTUTOR_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")`
  4. Run `chmod 600 deploy/.env`.
- [ ] **Step 5 (Thomas): Start the app.**
  - From `/srv/mathtutor`, run `docker build -t mathtutor:local .`, then `docker compose -f deploy/compose.yaml up -d`.
  - Building on the host is temporary. Milestone D replaces it with digest deploys from CI.
- [ ] **Step 6: Verify from outside AWS** (laptop). Every check must pass; paste the outputs into `host.md`.
  - `curl -sS https://<domain>/readyz` → `{"status":"ready",...,"servable":6}`
  - `curl -sI http://<domain>/` → a 308 redirect to `https://`
  - `curl -sI https://<domain>/healthz` shows the `content-security-policy` header
  - `curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://<static-ip>:8000/` → fails or times out, because port 8000 is not exposed
- [ ] **Step 7: Measure memory as a first data point** (this doesn't finalise sizing; spec 09).
  - On the host, run `free -m` and `docker stats --no-stream`.
  - Record the idle RAM for the app, Caddy and the OS in `host.md`.
- [ ] **Step 8: Write `runbook.md`** (≤ 60 lines). It covers:
  - **update:** `git pull`, rebuild, `up -d`, verify `/readyz`
  - **logs:** `docker compose logs -f app`
  - **restart**
  - **rollback:** check out the previous commit or tag, rebuild, `up -d`
  - **rotate secret**
  - **where `.env` lives**, and that it's never committed
  - **what the budget alert is and isn't**
- [ ] **Step 9: Check for secrets.**
  - Run `git grep -nI -e MATHTUTOR_SECRET_KEY= -e AKIA -e "BEGIN .*PRIVATE KEY"`.
  - Expected: only the empty example line in `deploy/.env.example`.
- [ ] **Step 10:** Fill in the actual hours in `docs/ops/hours.md`, and run `uv run python tools/check_docs.py`.
- [ ] **Step 11: Commit** with the message `docs: deploy milestone A skeleton; host record and runbook`.
  - Then tag the commit `milestone-a` (`git tag milestone-a`) only after Thomas confirms the exit evidence in the [plan README](../README.md#exit-evidence-from-01-foundation).
