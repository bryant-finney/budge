# Parse rules.md (read with `jq -Rs`) into {rulesets: [<POST /rulesets payload>], settings: {...}}.
# rules.md documents the table format.

def strip: gsub("^\\s+|\\s+$"; "");
def unspan: gsub("`"; "");
def cells: strip | ltrimstr("|") | rtrimstr("|") | split("|") | map(strip);
def spans: [scan("`([^`]*)`") | .[0]];
def parse: . as $s | try fromjson catch $s;
# a scalar cell: its first code span read as JSON, else as a string
def value: ((spans | first) // .) | parse;
# a list cell: every code span in it ("none" has none)
def list: spans | map(parse);
# index of the ruleset being filled
def cur: (.rulesets | length) - 1;

reduce (split("\n")[]) as $line ({rulesets: [], settings: {}, section: null, table: null};
  if ($line | startswith("## ")) then
    ($line[3:] | unspan | strip) as $heading
    | .table = null
    | if ($heading | startswith("Ruleset ")) then
        .section = "ruleset"
        | .rulesets += [{
            name: ($heading[8:] | strip),
            target: null,
            enforcement: "active",
            conditions: {ref_name: {include: [], exclude: []}},
            bypass_actors: [],
            rules: []
          }]
      elif $heading == "Repository settings" then .section = "settings"
      else .section = null
      end
  elif ($line | startswith("|") | not) then .table = null
  elif .section == null then .
  else
    ($line | cells) as $c
    | if ($c[0] | test("^:?-+:?$")) then .
      # the first row of a table is its header, which names the table
      elif .table == null then .table = ($c[0] | ascii_downcase)
      elif .section == "settings" then .settings[$c[0] | unspan] = ($c[1] | value)
      elif .table == "setting" then
        ($c[0] | unspan) as $key
        | if $key == "target" or $key == "enforcement" then
            .rulesets[cur][$key] = ($c[1] | value)
          elif $key == "include" or $key == "exclude" then
            .rulesets[cur].conditions.ref_name[$key] = ($c[1] | list)
          elif $key == "bypass_actors" then .rulesets[cur].bypass_actors = ($c[1] | list)
          else error("ruleset \(.rulesets[cur].name): unknown setting \($key)")
          end
      elif .table == "rule" then
        ($c[0] | unspan) as $type
        | ($c[1] | unspan) as $param
        | if (.rulesets[cur].rules | map(.type) | index($type)) == null then
            .rulesets[cur].rules += [{type: $type}]
          else .
          end
        | (.rulesets[cur].rules | map(.type) | index($type)) as $i
        | if $param == "" then .
          else .rulesets[cur].rules[$i].parameters[$param] = ($c[2] | value)
          end
      else error("unknown table \"\(.table)\" in ruleset \(.rulesets[cur].name)")
      end
  end)
| {rulesets, settings}
| .rulesets[] |= (if .target == null then error("ruleset \(.name): no target") else . end)
