# Production host

[Operations](README.md) · [Runbook](runbook.md)

Fill in each `TBD` as task 8 proceeds. Never record credentials, keys or the contents of `.env`.

## Cost controls

- **AWS Budget:** $10/month alert to Thomas's email, created TBD.
  It is a **notification, not a spending cap**: AWS keeps billing past it.

## Instance

| Field | Value |
|---|---|
| Provider | AWS Lightsail |
| Region | Oregon, us-west-2 (zone us-west-2a) |
| Bundle / RAM | General purpose: 1 GB RAM, 2 vCPUs, 40 GB SSD |
| OS | Ubuntu 24.04 LTS |
| Static IPv4 | `44.231.68.211` (Lightsail static IP) |
| IPv6 | Dual-stack (IPv6 assigned; no `AAAA` record yet) |
| Monthly price (date checked) | $7/month (2026-10-15) |
| Firewall | 22: Thomas's IPv4 + Lightsail browser SSH; 80: any IPv4/IPv6; 443: any IPv4 |

## Domain

| Field | Value |
|---|---|
| Domain | `thomasgragossian.dev` (registered 2026-10-15); app at `tutor.thomasgragossian.dev` |
| Registrar / DNS | Cloudflare (registrar and DNS) |
| Yearly cost | $8.20 first year, $12.20/yr renewal |
| Records | `A` → static IPv4 (`AAAA` only if IPv6 is enabled); DNS-only, no proxy |

## Layout on the host

- Checkout: `/srv/mathtutor` (public repo, cloned over HTTPS).
- Secrets: `/srv/mathtutor/deploy/.env`, mode 600, exists only on the host.
- Setup script: [`deploy/bootstrap.sh`](../../deploy/bootstrap.sh) (Docker, unattended upgrades, 1 GB swap).
- Deploy method until milestone D: build from the checkout on the host (`mathtutor:local`).

## Verification from outside AWS

Checked 2026-10-15 16:57 UTC from Thomas's laptop (outside AWS). All four pass.
TLS: Let's Encrypt certificate for `tutor.thomasgragossian.dev`, expires 2027-01-13 (Caddy renews).

```text
$ curl -sS https://tutor.thomasgragossian.dev/readyz
{"status":"ready","content_version":"36c7219f7f63","servable":6}
$ curl -sI http://tutor.thomasgragossian.dev/
HTTP/1.1 308 Permanent Redirect
Location: https://tutor.thomasgragossian.dev/
$ curl -sI https://tutor.thomasgragossian.dev/healthz
HTTP 200
Content-Security-Policy: default-src 'self'
Referrer-Policy: same-origin
X-Content-Type-Options: nosniff
$ curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://44.231.68.211:8000/
000 (Connection timed out after 5022 milliseconds)
```

## Idle memory (first data point, not final sizing)

2026-10-15, idle after deploy.

```text
$ free -m
               total        used        free      shared  buff/cache   available
Mem:             909         454         150           2         431         455
Swap:           1023          30         993
```

```text
$ sudo docker stats --no-stream
NAME             CPU %     MEM USAGE / LIMIT     MEM %
deploy-caddy-1   0.03%     34.76MiB / 909.5MiB   3.82%
deploy-app-1     0.13%     57.45MiB / 909.5MiB   6.32%
```

App + Caddy idle ≈ 92 MiB; OS, Docker daemon and agents ≈ 360 MiB; ≈ 455 MiB available.
That headroom bounds milestone B's verifier pool; measure again then (spec 09).
