#!/usr/bin/env bash
# Starts (or restarts) an ISLE Docker environment and configures it for the Islandora Workbench
# integration tests. Works on Linux, macOS and Windows (WSL2 or Git Bash, with Docker Desktop).
#
# Usage:  scripts/isle/setup-isle-test-env.sh            # from anywhere
#
# Environment overrides (all optional):
#   ISLE_DIR            Where isle-site-template is (or will be) cloned.   Default: <repo>/isle-site-template
#   ISLE_REPO           Git URL of isle-site-template.
#   ISLANDORA_TAG       ISLE image tag.                                    Default: main
#   ISLE_HTTPS          auto | mkcert | http.  auto = mkcert, except http under WSL (mkcert is unsupported there).
#   ISLE_RESTART        1 = stop the stack before starting it (default: leave a running stack alone).
#   WB_ADMIN_PASSWORD, WB_TEST_USER, WB_TEST_USER_PASSWORD, WB_ROLE   Passed to provision-drupal.sh.

set -euo pipefail
#set -x

# isle-site-template's scripts call tput, which fails when TERM is unset or "dumb" (CI, some terminals/IDEs).
if [ -z "${TERM:-}" ] || [ "${TERM}" = "dumb" ]; then
  export TERM="xterm-256color"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ISLE_DIR="${ISLE_DIR:-${REPO_ROOT}/isle-site-template}"
ISLE_REPO="${ISLE_REPO:-https://github.com/Islandora-Devops/isle-site-template.git}"
ISLANDORA_TAG="${ISLANDORA_TAG:-main}"
ISLE_HTTPS="${ISLE_HTTPS:-auto}"
ISLE_RESTART="${ISLE_RESTART:-0}"
PERMISSIONS_FILE="${REPO_ROOT}/tests/assets/user-role-permissions.txt"
PROVISION_SCRIPT="${SCRIPT_DIR}/provision-drupal.sh"

die() { echo "Error: $*" >&2; exit 1; }
log() { printf '\n### %s\n' "$*"; }

is_wsl() { grep -qi microsoft /proc/version 2>/dev/null; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "'$1' is required but was not found. $2"
}

check_prerequisites() {
  need git "Install git."
  need docker "Install Docker (Docker Desktop on macOS/Windows)."
  need make "Install make (macOS: 'xcode-select --install'; Debian/Ubuntu: 'apt install make'; Windows: use WSL2)."
  need curl "Install curl."
  docker compose version >/dev/null 2>&1 || die "'docker compose' (v2) is required."
  docker info >/dev/null 2>&1 || die "The Docker daemon isn't running or isn't reachable. Start Docker and try again."
  [ -f "${PERMISSIONS_FILE}" ] || die "Missing ${PERMISSIONS_FILE}"
  [ -f "${PROVISION_SCRIPT}" ] || die "Missing ${PROVISION_SCRIPT}"
}

use_mkcert() {
  case "${ISLE_HTTPS}" in
    mkcert) return 0 ;;
    http) return 1 ;;
    auto) is_wsl && return 1 || return 0 ;;
    *) die "ISLE_HTTPS must be auto, mkcert or http (got '${ISLE_HTTPS}')." ;;
  esac
}

ensure_mkcert() {
  command -v mkcert >/dev/null 2>&1 && return 0

  local os arch dest="${HOME}/.local/bin"
  case "$(uname -s)" in
    Linux) os=linux ;;
    Darwin) os=darwin ;;
    MINGW* | MSYS* | CYGWIN*) os=windows ;;
    *) die "Unsupported OS for downloading mkcert. Install it manually: https://github.com/FiloSottile/mkcert" ;;
  esac
  case "$(uname -m)" in
    x86_64 | amd64) arch=amd64 ;;
    arm64 | aarch64) arch=arm64 ;;
    *) die "Unsupported CPU for downloading mkcert. Install it manually: https://github.com/FiloSottile/mkcert" ;;
  esac

  log "mkcert not found; downloading ${os}/${arch} to ${dest}"
  mkdir -p "${dest}"
  local exe="${dest}/mkcert"
  [ "${os}" = windows ] && exe="${exe}.exe"
  curl -fsSL -o "${exe}" "https://dl.filippo.io/mkcert/latest?for=${os}/${arch}"
  chmod +x "${exe}"
  export PATH="${dest}:${PATH}"
  command -v mkcert >/dev/null 2>&1 || die "mkcert was downloaded but isn't on PATH."
}

compose() { (cd "${ISLE_DIR}" && docker compose "$@"); }

start_stack() {
  if [ ! -d "${ISLE_DIR}" ]; then
    log "Cloning isle-site-template into ${ISLE_DIR}"
    git clone "${ISLE_REPO}" "${ISLE_DIR}"

    use_mkcert && ensure_mkcert

    log "Building and starting ISLE (this takes a while the first time)"
    (cd "${ISLE_DIR}" && make overwrite-starter-site init up \
      ISLANDORA_TAG="${ISLANDORA_TAG}" \
      ISLANDORA_STARTER_REF="heads/main" \
      ISLANDORA_STARTER_OWNER="Islandora-Devops" \
      GITHUB_ACTIONS="false" \
      TERM="${TERM}")

    if use_mkcert; then
      log "Switching Traefik to HTTPS with mkcert certificates"
      (cd "${ISLE_DIR}" && ./scripts/traefik-https-mkcert.sh)
      compose down traefik
      compose up -d traefik
    else
      log "Staying on HTTP (ISLE_HTTPS=${ISLE_HTTPS})"
    fi
  else
    log "Using existing ${ISLE_DIR}"
    if [ "${ISLE_RESTART}" = "1" ]; then
      compose down
    fi
    compose up -d
  fi

  log "Waiting for Drupal to come up"
  (cd "${ISLE_DIR}" && ./scripts/ping.sh)
}

provision_drupal() {
  log "Provisioning Drupal for the integration tests"
  # Strip blank lines and CRs (Windows checkouts), join with commas, drop the trailing comma.
  local permissions
  permissions="$(tr -d '\r' < "${PERMISSIONS_FILE}" | sed '/^[[:space:]]*$/d' | paste -sd, -)"

  # -T: no TTY (works in CI and Git Bash). The script is piped in so the commands run in Linux, inside the container.
  compose exec -T \
    -e WB_PERMISSIONS="${permissions}" \
    -e WB_ADMIN_PASSWORD="${WB_ADMIN_PASSWORD:-admin}" \
    -e WB_TEST_USER="${WB_TEST_USER:-test-user}" \
    -e WB_TEST_USER_PASSWORD="${WB_TEST_USER_PASSWORD:-testPassword}" \
    -e WB_ROLE="${WB_ROLE:-workbench_user}" \
    drupal bash -s < "${PROVISION_SCRIPT}"
}

check_prerequisites
start_stack
provision_drupal

echo
echo "Done setting up ISLE for integration tests."
