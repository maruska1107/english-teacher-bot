#!/usr/bin/env bash
set -euo pipefail

readonly repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly test_image="english-teacher-bot-test:local"

fail() {
  printf 'test gate error: %s\n' "$*" >&2
  exit 1
}

command -v node >/dev/null 2>&1 || fail "Node.js 18 or newer is required; JavaScript security tests were not run."
node_major="$(node -p 'Number(process.versions.node.split(".")[0])')" \
  || fail "unable to determine the installed Node.js version."
[[ "$node_major" =~ ^[0-9]+$ ]] || fail "unexpected Node.js version: $(node --version 2>&1)"
(( node_major >= 18 )) \
  || fail "Node.js 18 or newer is required (found $(node --version)); JavaScript security tests were not run."

command -v docker >/dev/null 2>&1 || fail "Docker is required to run the canonical Python and Ruff checks."
docker info >/dev/null 2>&1 || fail "Docker is installed, but the daemon is unavailable."

shopt -s nullglob
js_tests=("$repo_root"/tests/js/*.test.js)
(( ${#js_tests[@]} > 0 )) || fail "no JavaScript tests matched tests/js/*.test.js; refusing to skip the UI security suite."

printf '\n==> JavaScript tests (Node %s)\n' "$(node --version)"
node --test "${js_tests[@]}"

printf '\n==> Building isolated Python test image\n'
docker build --quiet --tag "$test_image" "$repo_root" >/dev/null

printf '\n==> Python tests and Ruff\n'
docker run --rm --user 0:0 --entrypoint sh \
  --volume "$repo_root/tests:/app/tests:ro" \
  --volume "$repo_root/app:/app/app:ro" \
  --volume "$repo_root/alembic:/app/alembic:ro" \
  --volume "$repo_root/pyproject.toml:/app/pyproject.toml:ro" \
  "$test_image" \
  -c 'pytest tests -q && ruff check app tests'

printf '\nAll test gate checks passed.\n'
