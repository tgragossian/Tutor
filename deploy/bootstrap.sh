#!/usr/bin/env bash
# One-time host setup for Ubuntu 24.04 LTS. Idempotent: safe to re-run.
# Usage: sudo bash bootstrap.sh   (never writes secrets)
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }
OWNER=${SUDO_USER:-ubuntu}
. /etc/os-release

apt-get update
apt-get install -y ca-certificates curl git unattended-upgrades

# Docker Engine + compose plugin from Docker's apt repository.
install -m 0755 -d /etc/apt/keyrings
if [ ! -s /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc]" \
  "https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

# Unattended security upgrades.
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
CONF

# 1 GB swap so image builds on a 1 GB instance don't hit the OOM killer.
if ! swapon --show | grep -q /swapfile; then
  [ -f /swapfile ] || { fallocate -l 1G /swapfile; chmod 600 /swapfile; mkswap /swapfile; }
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

install -d -m 0755 -o "$OWNER" -g "$OWNER" /srv/mathtutor

cat <<NEXT

Host ready. Next steps (as $OWNER):
  git clone https://github.com/tgragossian/Tutor.git /srv/mathtutor
  cd /srv/mathtutor && cp deploy/.env.example deploy/.env && chmod 600 deploy/.env
  # edit deploy/.env: SITE_ADDRESS=<domain>, MATHTUTOR_SECRET_KEY=<from the command below>
  python3 -c "import secrets; print(secrets.token_urlsafe(48))"
  sudo docker build -t mathtutor:local .
  sudo docker compose -f deploy/compose.yaml up -d
NEXT
