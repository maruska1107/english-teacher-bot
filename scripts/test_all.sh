#!/usr/bin/env bash
set -euo pipefail

readonly repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly inline_script_extractor="$repo_root/scripts/extract_inline_script.py"

fail() {
  printf 'test gate error: %s\n' "$*" >&2
  exit 1
}

command -v node >/dev/null 2>&1 || fail "Node.js 18 or newer is required; JavaScript checks were not run."
node_major="$(node -p 'Number(process.versions.node.split(".")[0])')" \
  || fail "unable to determine the installed Node.js version."
[[ "$node_major" =~ ^[0-9]+$ ]] || fail "unexpected Node.js version: $(node --version 2>&1)"
(( node_major >= 18 )) \
  || fail "Node.js 18 or newer is required (found $(node --version)); JavaScript checks were not run."

command -v python3 >/dev/null 2>&1 \
  || fail "Python 3 is required to extract production inline JavaScript safely."
[[ -f "$inline_script_extractor" ]] || fail "inline JavaScript extractor is missing: $inline_script_extractor"

command -v docker >/dev/null 2>&1 || fail "Docker is required to run the canonical Python and Ruff checks."
docker info >/dev/null 2>&1 || fail "Docker is installed, but the daemon is unavailable."

readonly dockerignore="$repo_root/.dockerignore"
[[ -f "$dockerignore" ]] || fail "Docker build context protection is missing: $dockerignore"
required_dockerignore_patterns=(.env '.env.*' .git .worktrees .venv venv backups)
for pattern in "${required_dockerignore_patterns[@]}"; do
  grep -Fqx -- "$pattern" "$dockerignore" \
    || fail ".dockerignore must exclude '$pattern' before Docker receives the build context."
done

shopt -s nullglob
js_tests=("$repo_root"/tests/js/*.test.js)
(( ${#js_tests[@]} > 0 )) || fail "no JavaScript tests matched tests/js/*.test.js; refusing to skip the UI security suite."

printf '\n==> JavaScript tests (Node %s)\n' "$(node --version)"
node --test "${js_tests[@]}"

inline_script_sources=(
  "$repo_root/app/api/student_webapp.py"
  "$repo_root/app/api/teacher_webapp.py"
)
printf '\n==> Production inline JavaScript syntax\n'
for source_path in "${inline_script_sources[@]}"; do
  [[ -f "$source_path" ]] || fail "production webapp source is missing: $source_path"
  printf 'Checking %s::SCRIPT\n' "${source_path#"$repo_root"/}"
  python3 "$inline_script_extractor" "$source_path" SCRIPT | node --check -
done

printf '\n==> Building isolated Python test image\n'
test_image_id="$(docker build --quiet "$repo_root")" \
  || fail "Docker failed to build the Python test image."
[[ -n "$test_image_id" && "$test_image_id" != *$'\n'* ]] \
  || fail "Docker returned an unexpected image ID: $test_image_id"
docker image inspect "$test_image_id" >/dev/null 2>&1 \
  || fail "Docker returned an unusable image ID: $test_image_id"
readonly test_image_id
printf 'Using immutable image %s\n' "$test_image_id"

printf '\n==> Python tests and Ruff\n'
docker run --rm --user 0:0 --entrypoint sh \
  --volume "$repo_root/tests:/app/tests:ro" \
  --volume "$repo_root/app:/app/app:ro" \
  --volume "$repo_root/alembic:/app/alembic:ro" \
  --volume "$repo_root/scripts:/app/scripts:ro" \
  --volume "$repo_root/pyproject.toml:/app/pyproject.toml:ro" \
  "$test_image_id" \
  -c 'pytest tests -q && ruff check app tests scripts'

printf '\nAll test gate checks passed.\n'
