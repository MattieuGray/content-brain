#!/usr/bin/env bash
# list_notes.sh <dir> [marker-key]
# Prints a deterministic, resumable work-list of markdown notes under <dir>:
#   <DONE|PENDING>\t<path>
# DONE  = the note's leading frontmatter block already contains <marker-key>
#         (default: cb_tagged), so a worker has already processed it.
# PENDING = not yet processed.
#
# This exists so coverage is counted from disk, never from memory. Build the
# list, count PENDING, work them down, then re-run and confirm PENDING is 0.
# Read-only: it lists, it never edits or copies anything.
set -u

DIR="${1:-}"
KEY="${2:-cb_tagged}"
if [ -z "$DIR" ]; then
  echo "usage: list_notes.sh <dir> [marker-key]" >&2
  exit 1
fi
if [ ! -d "$DIR" ]; then
  echo "not a directory: $DIR" >&2
  exit 1
fi

find "$DIR" -type f -name '*.md' 2>/dev/null | sort | while IFS= read -r f; do
  # Search only the leading --- frontmatter block for the marker key.
  if awk -v key="$KEY" '
      NR==1 && $0 !~ /^---[[:space:]]*$/ { exit }        # file has no frontmatter
      NR>1  && /^---[[:space:]]*$/       { exit }         # end of frontmatter, key absent
      NR>1  && $0 ~ "^"key"[[:space:]]*:" { found=1; exit }  # marker found
      END { exit (found ? 0 : 1) }
    ' "$f"; then
    printf 'DONE\t%s\n' "$f"
  else
    printf 'PENDING\t%s\n' "$f"
  fi
done

printf 'LIST_DONE\t%s\n' "$DIR"
