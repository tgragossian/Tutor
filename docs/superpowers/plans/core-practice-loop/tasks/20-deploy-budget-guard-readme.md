[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 896–933. Review findings remain unresolved.

### Task 20: Deploy, budget guard, README

Manual AWS steps are listed for you, the developer, to perform. Claude does not create cloud resources.

**Files:**
- Create: `.github/workflows/deploy.yml`, `docs/deploy.md`
- Modify: `README.md`

**Interfaces:**
- **`deploy.yml`:**
  - on push to `main` after CI passes, build and push `ghcr.io/<owner>/mathtutor:<sha>` and `:latest`
  - SSH to the host (secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`)
  - run `docker compose pull && docker compose up -d`
  - then `curl -fsS https://$DOMAIN/healthz`
- **`docs/deploy.md`, a checklist for you:**
  - Lightsail $5 instance with Docker installed and a static IP
  - domain A record pointing at it
  - S3 bucket plus an IAM user restricted to that bucket
  - `.env` on the host
  - the crontab line for `backup.sh`
  - an AWS Budget of $10/month with an email alert
- **README:**
  - what it is
  - an architecture diagram (Mermaid)
  - how to run locally (`uv sync`, `.env.example`, `uv run uvicorn …`)
  - how to run the tests and the evaluation
  - the latest `eval/report.md` table
  - limitations (from §1.3 and the risks)
  - roadmap to sub-projects 2–4

- [ ] **Step 1:** Add the `tests/test_readme.py` check: the README contains the section headings "Architecture", "Run locally", "Verifier evaluation" and "Limitations", and `.env.example` lists `SECRET_KEY` and `DATABASE_URL`. Run it: FAIL, then write the docs, then PASS.
- [ ] **Step 2:** You do the `docs/deploy.md` checklist. Then push to `main`.
- [ ] **Step 3: Verify (§11).**
  - `https://<domain>/healthz` returns ok.
  - Both CI and deploy workflows pass.
  - One manual diagnostic, practice and recap run on the live site succeeds.
  - Record the results in the README.
- [ ] **Step 4: Commit** `docs: deployment workflow, README, deploy checklist`.
<!-- End preserved source. -->
