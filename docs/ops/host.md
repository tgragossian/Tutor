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
| Region | TBD |
| Bundle / RAM | TBD (at least 1 GB) |
| OS | Ubuntu 24.04 LTS |
| Static IPv4 | TBD |
| IPv6 | TBD (enabled or not) |
| Monthly price (date checked) | TBD |
| Firewall | 22 from Thomas's IP only; 80 and 443 from anywhere; nothing else |

## Domain

| Field | Value |
|---|---|
| Domain | TBD |
| Registrar / DNS | TBD |
| Yearly cost | TBD |
| Records | `A` → static IPv4 (`AAAA` only if IPv6 is enabled); DNS-only, no proxy |

## Layout on the host

- Checkout: `/srv/mathtutor` (public repo, cloned over HTTPS).
- Secrets: `/srv/mathtutor/deploy/.env`, mode 600, exists only on the host.
- Setup script: [`deploy/bootstrap.sh`](../../deploy/bootstrap.sh) (Docker, unattended upgrades, 1 GB swap).
- Deploy method until milestone D: build from the checkout on the host (`mathtutor:local`).

## Verification from outside AWS

Paste the real outputs here, with the date.

```text
$ curl -sS https://<domain>/readyz
TBD
$ curl -sI http://<domain>/            # expect 308 to https://
TBD
$ curl -sI https://<domain>/healthz    # expect content-security-policy header
TBD
$ curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://<static-ip>:8000/   # expect failure
TBD
```

## Idle memory (first data point, not final sizing)

```text
$ free -m
TBD
$ sudo docker stats --no-stream
TBD
```
