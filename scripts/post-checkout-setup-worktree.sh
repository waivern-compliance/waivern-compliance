#!/usr/bin/env bash
# Post-checkout hook: set up a newly-created git worktree by symlinking
# gitignored local files (env, local plans, Claude settings) and the per-project
# Claude memory directory from the main worktree. Symlinks (not copies) so that
# edits propagate both ways and survive `git worktree remove`.
#
# Fires only on fresh worktree creation:
#   - prev_HEAD is all zeros (no previous checkout in this worktree)
#   - branch_flag is 1 (branch checkout, not file checkout)
#   - we're inside a worktree, not the main repo
#
# Wired in via .pre-commit-config.yaml. Activate on a new clone with:
#   pre-commit install --hook-type post-checkout

set -euo pipefail

prev_head="${PRE_COMMIT_FROM_REF:-${1:-}}"
branch_flag="${PRE_COMMIT_CHECKOUT_TYPE:-${3:-}}"

[[ "${branch_flag}" == "1" ]] || exit 0
[[ "${prev_head}" =~ ^0+$ ]] || exit 0

main_worktree="$(git worktree list --porcelain | awk '/^worktree / {print $2; exit}')"
current_worktree="$(git rev-parse --show-toplevel)"

[[ "${main_worktree}" != "${current_worktree}" ]] || exit 0

echo "post-checkout: setting up worktree at ${current_worktree}"

paths_to_symlink=(
  ".env"
  ".local"
  ".claude/settings.local.json"
)

for path in "${paths_to_symlink[@]}"; do
  src="${main_worktree}/${path}"
  dst="${current_worktree}/${path}"
  if [[ -e "${src}" && ! -e "${dst}" ]]; then
    mkdir -p "$(dirname "${dst}")"
    ln -s "${src}" "${dst}"
    echo "  symlinked ${path}"
  fi
done

encode_path() {
  printf '%s' "$1" | tr '/' '-'
}

main_memory_dir="${HOME}/.claude/projects/$(encode_path "${main_worktree}")/memory"
worktree_memory_dir="${HOME}/.claude/projects/$(encode_path "${current_worktree}")/memory"

if [[ -d "${main_memory_dir}" && ! -e "${worktree_memory_dir}" ]]; then
  mkdir -p "$(dirname "${worktree_memory_dir}")"
  ln -s "${main_memory_dir}" "${worktree_memory_dir}"
  echo "  symlinked Claude memory -> ${main_memory_dir}"
fi

echo "post-checkout: done"
