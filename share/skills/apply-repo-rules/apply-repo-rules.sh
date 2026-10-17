#!/usr/bin/env bash
# Check or apply the repo's rulesets and merge settings, as defined by the tables in rules.md.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: apply-repo-rules.sh check [REF]
       apply-repo-rules.sh apply
       apply-repo-rules.sh apply-ref REF

  check      compare the live GitHub settings with rules.md at REF (default origin/main);
             read-only; exit 1 on drift
  apply      create or update rulesets and merge settings to match rules.md on origin/main,
             then check
  apply-ref  the same as apply, but from REF; needs the user's approval every time
EOF
}

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# A GET adds server fields (id, node_id, _links, ...); compare only the keys a payload sets, with
# rules sorted by type because `jq -S` sorts object keys but not array elements
keys='{name, target, enforcement, bypass_actors, conditions, rules: (.rules | sort_by(.type))}'

# load_desired REF: parse rules.md as committed at REF into $desired
load_desired() {
  local path
  path="$(git -C "$here" rev-parse --show-prefix)rules.md"
  if ! git -C "$here" cat-file -e "$1:$path" 2>/dev/null; then
    echo "$path doesn't exist at $1" >&2
    exit 2
  fi
  echo "desired: $path at $1 ($(git -C "$here" rev-parse --short "$1"))"
  desired=$(git -C "$here" show "$1:$path" | jq -Rs -f "$here/parse-rules.jq")
}

# ruleset_id NAME: print the id of the repo's ruleset called NAME, or nothing if it doesn't exist
ruleset_id() {
  gh api --paginate "repos/$repo/rulesets" --jq ".[] | select(.name == \"$1\") | .id"
}

# diff_ruleset PAYLOAD ID: diff a desired ruleset payload against live ruleset ID
diff_ruleset() {
  local name
  name=$(jq -r .name <<<"$1")
  diff -u --label "desired/$name" --label "live/$name" \
    <(jq -S "$keys" <<<"$1") <(gh api "repos/$repo/rulesets/$2" | jq -S "$keys")
}

# diff_settings: diff the desired repo settings against the same fields of the live repo
diff_settings() {
  diff -u --label desired/settings --label live/settings \
    <(jq -S .settings <<<"$desired") \
    <(gh api "repos/$repo" | jq -S --argjson want "$(jq .settings <<<"$desired")" \
      '. as $live | $want | with_entries(.value = $live[.key])')
}

check() {
  local drift=0 payload name id extra
  while IFS= read -r payload <&3; do
    name=$(jq -r .name <<<"$payload")
    id=$(ruleset_id "$name")
    if [[ -z $id ]]; then
      echo "FAIL ruleset $name: missing"
      drift=1
    elif diff_ruleset "$payload" "$id"; then
      echo "OK   ruleset $name"
    else
      echo "FAIL ruleset $name: differs (diff above)"
      drift=1
    fi
  done 3< <(jq -c '.rulesets[]' <<<"$desired")

  extra=$(comm -13 <(jq -r '.rulesets[].name' <<<"$desired" | sort) \
    <(gh api --paginate "repos/$repo/rulesets" --jq '.[].name' | sort))
  if [[ -n $extra ]]; then
    echo "FAIL rulesets not in rules.md: $(paste -sd, - <<<"$extra")"
    drift=1
  fi

  if diff_settings; then
    echo "OK   repo settings"
  else
    echo "FAIL repo settings: differ (diff above)"
    drift=1
  fi
  return "$drift"
}

apply() {
  local payload name id
  while IFS= read -r payload <&3; do
    name=$(jq -r .name <<<"$payload")
    id=$(ruleset_id "$name")
    if [[ -z $id ]]; then
      echo "create ruleset $name"
      gh api --method POST "repos/$repo/rulesets" --input - \
        --jq '{id, name, enforcement}' <<<"$payload"
    elif ! diff_ruleset "$payload" "$id" >/dev/null; then
      echo "update ruleset $name ($id)"
      gh api --method PUT "repos/$repo/rulesets/$id" --input - \
        --jq '{id, name, enforcement}' <<<"$payload"
    else
      echo "keep   ruleset $name"
    fi
  done 3< <(jq -c '.rulesets[]' <<<"$desired")

  if diff_settings >/dev/null; then
    echo "keep   repo settings"
  else
    echo "update repo settings"
    jq .settings <<<"$desired" | gh api --method PATCH "repos/$repo" --input - >/dev/null
  fi

  echo
  check
}

case "${1:-}" in
  check)
    [[ $# -le 2 ]] || { usage >&2; exit 64; }
    command=check ref=${2:-origin/main}
    ;;
  apply)
    [[ $# -eq 1 ]] || { usage >&2; exit 64; }
    command=apply ref=origin/main
    ;;
  apply-ref)
    [[ $# -eq 2 ]] || { usage >&2; exit 64; }
    command=apply ref=$2
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 64
    ;;
esac

if [[ $ref == origin/main ]]; then
  git -C "$here" fetch --quiet origin main
fi
load_desired "$ref"
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
echo "repo:    $repo"
"$command"
