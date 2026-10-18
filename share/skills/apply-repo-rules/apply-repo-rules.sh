#!/usr/bin/env bash
# Check or apply the repo's rulesets and merge settings, as defined by the tables in rules.md.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: apply-repo-rules.sh check [REF]
       apply-repo-rules.sh apply
       apply-repo-rules.sh apply-ref REF

  check      compare the live GitHub settings with rules.md at REF (default: main, fetched from
             GitHub); read-only
  apply      create or update rulesets and merge settings to match rules.md on main, fetched
             from GitHub, then check; refuses unless this directory matches that commit
  apply-ref  the same as apply, but from REF; needs the user's approval every time

exit status:
  0   no drift
  1   drift (check)
  2   REF, rules.md, or parse-rules.jq is missing at the ref, or rules.md doesn't parse
  3   can't fetch main from GitHub
  4   apply refused: this directory differs from the main commit it would apply
  5   a GitHub API call failed, or its result is ambiguous (two rulesets with one name)
  64  usage
EOF
}

# The target is fixed, not read from git remotes or gh's config, so local config can't redirect
# where this reads from or writes to.
repo=bryant-finney/budge
host=github.com
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)

# The parameter names each rule type in $want (a desired ruleset) sets
# shellcheck disable=SC2016 # $want and $pk are jq variables
pk='($want.rules | map({key: .type, value: ((.parameters // {}) | keys)}) | from_entries) as $pk'
# Reduce a ruleset to the keys $want sets. A GET adds server fields (id, node_id, _links, ...) and
# rule parameters with server defaults, so keep only the parameters $want names. Sort rules by
# type, because `jq -S` sorts object keys but not array elements.
# shellcheck disable=SC2016 # $want and $pk are jq variables
project="$pk"'
  | {name, target, enforcement, conditions,
     bypass_actors: ((.bypass_actors // []) | sort_by(.actor_type, .actor_id)),
     rules: (.rules
       | map(.type as $t
         | if .parameters and $pk[$t] then
             .parameters |= with_entries(select(.key | IN($pk[$t][])))
           else . end
         | if .parameters == {} then del(.parameters) else . end)
       | sort_by(.type))}'
# The live parameters, per rule type, that $want doesn't set, and so that check doesn't compare
# shellcheck disable=SC2016 # $want and $pk are jq variables
unset_params="$pk"'
  | .rules[] | select(.parameters and $pk[.type]) | .type as $t
  | [.parameters | keys[] | select(IN($pk[$t][]) | not)]
  | select(length > 0) | "\($t): \(join(", "))"'

# die CODE MESSAGE: print MESSAGE to stderr and exit with CODE. In a command substitution this
# exits only the subshell, so callers there add `|| exit $?`.
die() {
  echo "apply-repo-rules: $2" >&2
  exit "$1"
}

# api ARGS...: call `gh api` on $host, whatever GH_HOST says; exit 5 if it fails
api() {
  gh api --hostname "$host" "$@" || die 5 "gh api $* failed"
}

# load_desired COMMIT LABEL: parse rules.md with parse-rules.jq, both as committed at COMMIT, into
# $desired
load_desired() {
  local prefix f parser
  prefix=$(git -C "$here" rev-parse --show-prefix)
  for f in rules.md parse-rules.jq; do
    git -C "$here" cat-file -e "$1:$prefix$f" 2>/dev/null || die 2 "$prefix$f doesn't exist at $2"
  done
  echo "desired: ${prefix}rules.md at $2 ($(git -C "$here" rev-parse --short "$1"))"
  parser=$(git -C "$here" show "$1:${prefix}parse-rules.jq")
  desired=$(git -C "$here" show "$1:${prefix}rules.md" | jq -Rs "$parser") \
    || die 2 "can't parse ${prefix}rules.md at $2"
  jq -e '(.rulesets | length) + (.settings | length) > 0' <<<"$desired" >/dev/null \
    || die 2 "${prefix}rules.md at $2 defines nothing"
}

# ruleset_id NAME: print the id of the repo's own ruleset called NAME (not an inherited one), or
# nothing if there is none; exit 5 if more than one has that name
ruleset_id() {
  local list ids
  list=$(api --paginate "repos/$repo/rulesets?includes_parents=false") || exit "$?"
  ids=$(jq -rs --arg name "$1" '[.[][] | select(.name == $name) | .id | tostring] | join(",")' \
    <<<"$list") || die 5 "can't read the list of rulesets"
  [[ $ids != *,* ]] || die 5 "more than one ruleset is named $1 (ids $ids); resolve it by hand"
  printf '%s' "$ids"
}

# diff_ruleset PAYLOAD ID: diff a desired ruleset payload against live ruleset ID, comparing only
# the keys PAYLOAD sets, and print a NOTE for live parameters it doesn't set. Returns 1 when they
# differ. Exits rather than returns on errors, because callers run it as an `if` condition, where
# `set -e` is off.
diff_ruleset() {
  local name live want got
  name=$(jq -r .name <<<"$1")
  live=$(api "repos/$repo/rulesets/$2") || exit "$?"
  want=$(jq -eS --argjson want "$1" "$project" <<<"$1") || die 5 "can't project ruleset $name"
  got=$(jq -eS --argjson want "$1" "$project" <<<"$live") \
    || die 5 "can't project live ruleset $name ($2)"
  jq -r --argjson want "$1" "$unset_params" <<<"$live" \
    | sed "s/^/NOTE ruleset $name: not in rules.md, so not compared: /" \
    || die 5 "can't list the unset parameters of live ruleset $name ($2)"
  diff -u --label "desired/$name" --label "live/$name" \
    <(printf '%s\n' "$want") <(printf '%s\n' "$got")
}

# diff_settings: diff the desired repo settings against the same fields of the live repo. Exits on
# errors, like diff_ruleset.
diff_settings() {
  local live want got
  want=$(jq -eS .settings <<<"$desired") || die 5 "can't read the desired repo settings"
  live=$(api "repos/$repo") || exit "$?"
  got=$(jq -eS --argjson want "$want" '. as $live | $want | with_entries(.value = $live[.key])' \
    <<<"$live") || die 5 "can't project the live repo settings"
  diff -u --label desired/settings --label live/settings \
    <(printf '%s\n' "$want") <(printf '%s\n' "$got")
}

check() {
  local drift=0 payload name id live_names extra
  while IFS= read -r payload <&3; do
    name=$(jq -r .name <<<"$payload")
    id=$(ruleset_id "$name") || exit "$?"
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

  live_names=$(api --paginate "repos/$repo/rulesets?includes_parents=false" --jq '.[].name') \
    || exit "$?"
  extra=$(jq -rn --argjson want "$(jq '[.rulesets[].name]' <<<"$desired")" \
    --arg live "$live_names" \
    '$live | split("\n") | map(select(. != "" and (IN($want[]) | not))) | join(", ")')
  if [[ -n $extra ]]; then
    echo "FAIL rulesets not in rules.md: $extra"
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
    id=$(ruleset_id "$name") || exit "$?"
    if [[ -z $id ]]; then
      echo "create ruleset $name"
      api --method POST "repos/$repo/rulesets" --input - \
        --jq '{id, name, enforcement}' <<<"$payload"
    elif ! diff_ruleset "$payload" "$id" >/dev/null; then
      echo "update ruleset $name ($id)"
      api --method PUT "repos/$repo/rulesets/$id" --input - \
        --jq '{id, name, enforcement}' <<<"$payload"
    else
      echo "keep   ruleset $name"
    fi
  done 3< <(jq -c '.rulesets[]' <<<"$desired")

  if diff_settings >/dev/null; then
    echo "keep   repo settings"
  else
    echo "update repo settings"
    jq .settings <<<"$desired" | api --method PATCH "repos/$repo" --input - >/dev/null
  fi

  echo
  check
}

case "${1:-}" in
  check)
    [[ $# -le 2 ]] || { usage >&2; exit 64; }
    command=check ref=${2:-}
    ;;
  apply)
    [[ $# -eq 1 ]] || { usage >&2; exit 64; }
    command=apply ref=
    ;;
  apply-ref)
    [[ $# -eq 2 && -n $2 ]] || { usage >&2; exit 64; }
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

if [[ -z $ref ]]; then
  # Ask the API where main is, then fetch from an explicit URL rather than the `origin` remote. A
  # commit is named by its content, so once the object is here, its source doesn't matter. Never
  # fall back to a cached copy: apply could then reapply rules from before the latest merge.
  src=$(api "repos/$repo/commits/main" --jq .sha)
  git -C "$here" fetch --quiet --no-tags "https://$host/$repo.git" main \
    || die 3 "can't fetch main from https://$host/$repo.git; not using a cached copy"
  git -C "$here" cat-file -e "$src^{commit}" 2>/dev/null \
    || die 3 "main is at $src on $host, but the fetch didn't bring that commit"
  label="main on $host"
else
  src=$(git -C "$here" rev-parse --verify --quiet "$ref^{commit}") || die 2 "$ref isn't a commit"
  label=$ref
fi
load_desired "$src" "$label"

# `apply` is pre-approved because merging rules.md is the approval, so it runs only the code that
# was merged with it. This stops an accidental apply from an edited working tree, not an edited
# copy of this script, which can drop the check.
if [[ $command == apply && -z $ref ]] \
  && ! git -C "$here" diff --quiet --no-ext-diff "$src" -- .; then
  git -C "$here" diff --stat "$src" -- . >&2 || true
  die 4 "refusing to apply: $here differs from $label ($(git -C "$here" rev-parse --short "$src"));
run apply from a checkout of that commit"
fi

echo "repo:    $repo"
"$command"
