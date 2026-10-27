# Runbook: C1 help

[Operations](README.md) · [Runbook](runbook.md) · [Host sizing](host-sizing.md) ·
[C1 status](../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md)

Same conventions as the [runbook](runbook.md): host commands run from `/srv/mathtutor`, with
`C="sudo docker compose -f deploy/compose.yaml"`. Never put a key in git, chat or a command line.

## Set the Anthropic key

1. In the Anthropic console, set the **monthly spend limit** and turn **auto-reload off**
   (Thomas has $5 of credit; the ledger caps help spend separately).
2. On the host, edit the env file that `deploy/compose.yaml` loads (`env_file: .env`, so
   `deploy/.env`, mode 600, git-ignored):
   ```bash
   nano deploy/.env        # add: MATHTUTOR_ANTHROPIC_API_KEY=<key>
   $C up -d app            # recreates the container with the new value
   ```
3. `curl -fsS https://<domain>/readyz` returns `ready`. Without a key the app still starts and
   stays ready; items just carry `help: null`. Rotating: edit the same line, `$C up -d app`.
4. Never run `$C config` or paste `docker inspect` output anywhere: both print the value.

## Turn help off

```bash
nano deploy/.env        # add: MATHTUTOR_HELP_GENERATOR=off
$C up -d app
```

Items then carry `help: null` (no buttons), `/api/help` answers `unavailable` and `/readyz`
stays 200. Practice and grading are unchanged. Remove the line (or set `claude`) to turn it on.

## Guard pool memory

The leak guard runs in its own verifier-style pool. Each worker's address-space cap is
`MATHTUTOR_GUARD_POOL_MEMORY_MB` (default 384), beside `MATHTUTOR_POOL_MEMORY_MB` for grading.
Size both from the container measurement in [host sizing](host-sizing.md); on 1 GB the two
caps plus the app, Caddy and the OS do not fit the 85% rule on paper.

## Mixed-load measurement (owner, container)

Use the scripted generator (no provider spend, no key needed). On the 1 GB host, stop the live
stack first (`$C stop app`), build the image, then run the production image with the e2e
overlay on a throwaway project (its own volume; never touches live data):

```bash
E2E=1 bash tests/container/smoke.sh        # on a machine with Docker, clean tree
EC="sudo docker compose -f deploy/compose.yaml -f deploy/compose.e2e.yaml"
$EC up -d app          # 127.0.0.1:18001, scripted help; uses mathtutor:local (smoke.sh built it)
                       # or set MATHTUTOR_IMAGE
APP=mathtutor-e2e-app-1 bash tools/load/measure.sh http://127.0.0.1:18001 8 help 20
$EC down -v                                # removes only the e2e volume
$C start app
```

The tool creates `load_*` and `loadh_*` accounts in that throwaway database only. Index build time:
```bash
sudo docker run --rm mathtutor:local python -c "import time;from mathtutor.settings import Settings as S;from mathtutor.help.config import load_help_config as L;from mathtutor.retrieval.bm25 import Bm25Index as B;from mathtutor.retrieval.corpus import load_corpus as C;s=S();c=C(s.corpus_path);g=L(s.help_config_path);t=time.perf_counter();B.build(c,g.retrieval);print(round(time.perf_counter()-t,2),'s')"
```

Arguments: grading users (keep at most 8, the queue size, so any `verifier_busy` means help
starved grading), `help`, help users. For the brief's 20 + 20 run, use `... 20 help 20` and
expect grading `verifier_busy` replies from grading alone; the report then fails by design:
read the latencies, not the exit status. Record in [host sizing](host-sizing.md): RSS of web,
grading worker, guard worker and Caddy; index build time; grading p95 against the B baseline
(2370 ms at 16 users). Apply the rule (at most 85% of RAM). If 1 GB fails, move to 2 GB.

## Move to the 2 GB bundle (approved 2026-10-26)

Lightsail console: snapshot the instance, create a 2 GB instance from the snapshot, attach the
static IP (`44.231.68.211`), then on the host `git pull --ff-only`, rebuild and `$C up -d` as in
the [runbook](runbook.md). Check `/readyz`, update [host](host.md) with the new bundle and price.

## Owner release checklist

1. Review the 60 help cases and 40 retrieval queries, set `reviewed_by: tg`
   ([evals/help/README.md](../../evals/help/README.md), step 6).
2. Approve the 12 confusion labels, the 4 rewritten misconception notes, the help panel copy
   and the provider disclosure wording.
3. Paid dev run (`--max-usd 4`), blind audit, then **decide on the retrieval gate before the
   holdout**: dev Recall@6 is 0.79 against the 0.80 holdout gate.
4. One-shot holdout (cap = credit minus the sum of earlier `spent_micros` minus $0.30; the
   draft holdout once scored 0.576 on BM25, no label edited, see status page); write the chosen model
   into `help_config.json`.
5. Container smoke `E2E=1 bash tests/container/smoke.sh`, then the mixed-load measurement above.
6. Gate check, [deploy](runbook.md), set the key, `/readyz`; on the live site one cited hint
   on a wrong derivative and one abstention on an out-of-book question.
7. Commit `docs: C1 released` after the live check.
