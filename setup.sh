#!/usr/bin/env bash
# setup.sh — prepare a worktree for development. Idempotent; safe to re-run.
#
# Run this once per worktree after `git worktree add`. It also works in the main
# worktree (where local files are the source, so only the external store and
# dependency install do anything).
#
# Usage:
#   ./setup.sh              copy local files, link local store + Claude memory, install deps
#   ./setup.sh --no-install skip `uv sync` (refresh files + symlinks only)
set -euo pipefail

RUN_INSTALL=1
for arg in "$@"; do
  case "$arg" in
    --no-install) RUN_INSTALL=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
COMMON_DIR="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
MAIN_ROOT="$(dirname "$COMMON_DIR")"   # parent of the shared .git dir = main worktree

# Copy a gitignored file from the main tree into this worktree. Never clobbers
# an existing copy (branches may diverge). Pass `drift` to warn when the source
# has KEY= entries the existing copy lacks — only meaningful for env-style files.
copy_from_main() {
  local f="$1" check="${2:-}"
  local src="$MAIN_ROOT/$f"
  [ -e "$src" ] || { echo "  · no source for $f, skipping"; return; }
  if [ -e "$f" ]; then
    if [ "$check" = "drift" ]; then
      local missing
      missing="$(comm -23 \
        <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "$src" | sort -u) \
        <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "$f"   | sort -u) || true)"
      if [ -n "$missing" ]; then
        echo "  ! $f missing keys present in main: $(echo "$missing" | tr '\n' ' ')"
      fi
    fi
    return 0
  fi
  mkdir -p "$(dirname "$f")"
  cp "$src" "$f"
  echo "  ✓ copied $f"
}

# ── Local files — COPY from the main tree (never link) ────────────────────────
# Env files carry a key-drift warning; other local files are copied verbatim.
# Sources that don't exist are skipped, so this is a no-op in repos lacking them.
ENV_FILES=(
  .env
)
LOCAL_COPY_FILES=(
  .claude/settings.local.json
)

echo "→ Local files"
if [ "$MAIN_ROOT" = "$REPO_ROOT" ]; then
  echo "  · main worktree — this is the source, nothing to copy"
else
  for f in "${ENV_FILES[@]}";        do copy_from_main "$f" drift; done
  for f in "${LOCAL_COPY_FILES[@]}"; do copy_from_main "$f";       done
fi

# ── External local store — shared by every worktree ───────────────────────────
# Lives outside the repo (its own tooling dir), so it is untouched when a
# worktree is removed. Absolute anchor because worktrees live at varying
# locations, so no relative path to it would be stable. The `.local` symlink
# exposes it at a repo-relative path identical in every tree.
TOOLING_ROOT="${TOOLING_ROOT:-$HOME/Workspace/tooling}"
LOCAL_STORE="$TOOLING_ROOT/$(basename "$MAIN_ROOT")/.local"

echo "→ Local store"
mkdir -p "$LOCAL_STORE"
# `ln -sfn` only replaces an existing *symlink*; if `.local` is a real directory
# (e.g. a tool ran `mkdir -p .local/...` before setup), BSD ln leaves it in place
# and the link never takes. Migrate any such directory into the store, then link.
if [ -d .local ] && [ ! -L .local ]; then
  echo "  · .local is a real directory — migrating its contents into the store"
  # -n keeps files with clashing names from clobbering existing store entries.
  cp -Rn .local/. "$LOCAL_STORE/" 2>/dev/null || true
  rm -rf .local
fi
ln -sfn "$LOCAL_STORE" .local
echo "  ✓ linked .local → $LOCAL_STORE"

# ── Claude memory — shared across every worktree ──────────────────────────────
# Claude stores per-project memory under <claude-dir>/projects/<encoded-path>/memory,
# where <encoded-path> is the worktree's absolute path with each non-alphanumeric
# char → '-'. A new worktree has a different path, hence a different (empty) memory
# dir. Symlink it back to main's so memory is shared. Symlink (not copy): memory is
# one evolving store, not per-branch state. No-op in the main worktree (it is source).
encode_path() { printf '%s' "$1" | sed 's/[^A-Za-z0-9]/-/g'; }
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

if [ "$MAIN_ROOT" != "$REPO_ROOT" ]; then
  echo "→ Claude memory"
  main_memory="$CLAUDE_DIR/projects/$(encode_path "$MAIN_ROOT")/memory"
  this_memory="$CLAUDE_DIR/projects/$(encode_path "$REPO_ROOT")/memory"
  if [ ! -d "$main_memory" ]; then
    echo "  · no memory in main tree, skipping"
  else
    mkdir -p "$(dirname "$this_memory")"
    # Mirror the .local guard: if a Claude session in this worktree already made
    # a real memory dir, fold its contents into main before linking (ln -sfn on
    # BSD won't replace a real directory, so migrate it out of the way first).
    if [ -d "$this_memory" ] && [ ! -L "$this_memory" ]; then
      echo "  · worktree memory is a real directory — migrating into main tree"
      cp -Rn "$this_memory"/. "$main_memory/" 2>/dev/null || true
      rm -rf "$this_memory"
    fi
    ln -sfn "$main_memory" "$this_memory"
    echo "  ✓ linked Claude memory → $main_memory"
  fi
fi

# ── Dependencies — regenerable ────────────────────────────────────────────────
if [ "$RUN_INSTALL" -eq 1 ]; then
  echo "→ Installing dependencies"
  uv sync --all-groups --all-extras --all-packages
else
  echo "→ Skipping install (--no-install)"
fi

echo "✓ Worktree ready."
