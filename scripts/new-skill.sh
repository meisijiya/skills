#!/usr/bin/env bash
# new-skill.sh — scaffold a new skill from skills/.template/SKILL.md
# Usage: scripts/new-skill.sh <skill-name> [--dry-run]
# Validates the kebab-case name, refuses to overwrite, renders the template
# into skills/<name>/ with references/, scripts/, assets/ (each with .gitkeep).
# With --dry-run, prints intended actions without writing anything.

set -euo pipefail

usage() {
  echo "Usage: scripts/new-skill.sh <skill-name> [--dry-run]" >&2
  echo "  <skill-name>  kebab-case, 1-64 chars, matches ^[a-z0-9]+(-[a-z0-9]+)*\$" >&2
  echo "  --dry-run     print intended actions, do not write anything" >&2
}

# Resolve repo root: git toplevel if available, else the script's parent dir.
repo_root() {
  if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
  else
    cd "$(dirname "$0")/.." && pwd
  fi
}

# "hello-world" -> "Hello World"
title_from_name() {
  local name="$1" word title=""
  IFS='-' read -r -a parts <<< "$name"
  for word in "${parts[@]}"; do
    title="${title} ${word^}"
  done
  printf '%s\n' "${title# }"
}

main() {
  local name="${1:-}" dry_run=false

  if [[ -z "$name" ]]; then
    usage
    exit 1
  fi
  if [[ "${2:-}" == "--dry-run" ]]; then
    dry_run=true
  elif [[ -n "${2:-}" ]]; then
    usage
    exit 1
  fi

  # 1. Validate name.
  if [[ ! "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
    echo "Error: '$name' is not a valid skill name (must match ^[a-z0-9]+(-[a-z0-9]+)*\$)" >&2
    exit 1
  fi
  if [[ ${#name} -gt 64 ]]; then
    echo "Error: '$name' is longer than 64 chars" >&2
    exit 1
  fi

  local root skill_dir template title
  root="$(repo_root)"
  skill_dir="$root/skills/$name"
  template="$root/skills/.template/SKILL.md"

  if [[ ! -f "$template" ]]; then
    echo "Error: template not found at $template" >&2
    exit 1
  fi

  title="$(title_from_name "$name")"

  echo "Would create skill '$name' ($title) at: $skill_dir"
  echo "  mkdir -p $skill_dir/{references,scripts,assets}"
  echo "  touch .gitkeep in each subdir"
  echo "  render template -> $skill_dir/SKILL.md (replace <skill-name-kebab-case> with $name, <Skill Title> with $title)"

  if [[ "$dry_run" == true ]]; then
    if [[ -e "$skill_dir/SKILL.md" || -d "$skill_dir" ]]; then
      echo "[dry-run] note: skill '$name' already exists — a real run would refuse to overwrite"
    else
      echo "[dry-run] no files written"
    fi
    return 0
  fi

  # Refuse to overwrite an existing skill.
  if [[ -e "$skill_dir/SKILL.md" || -d "$skill_dir" ]]; then
    echo "Error: skill '$name' already exists at $skill_dir (refusing to overwrite)" >&2
    exit 1
  fi
  mkdir -p "$skill_dir/references" "$skill_dir/scripts" "$skill_dir/assets"
  touch "$skill_dir/references/.gitkeep" "$skill_dir/scripts/.gitkeep" "$skill_dir/assets/.gitkeep"
  sed -e "s/<skill-name-kebab-case>/$name/g" -e "s/<Skill Title>/$title/g" \
    "$template" > "$skill_dir/SKILL.md"

  echo "Created skill '$name' at $skill_dir"
  echo "Next: edit $skill_dir/SKILL.md and replace every <!-- TODO: ... --> marker."
}

main "$@"
