# GitHub operations

Prefer a connected GitHub tool when it supports the operation and has the required permission.
If integration permissions are insufficient, report the failure and use an already authorized,
authenticated `gh` CLI. Do not treat an approval-review rejection as an integration limitation.

## Read complete activity

`gh pr list --state open --limit 100 --json number,url,headRefName,headRefOid,baseRefName,labels`
is a useful inventory; paginate if the limit is reached. The `latestReviews` and `reviewDecision`
summary fields can be empty despite submitted approvals. They are not a complete activity feed.

Fetch discussion comments, submitted reviews, and review threads separately. This GraphQL query
is a per-PR starting point; pass `owner`, `name`, and `number` using the chosen client's variables:

```graphql
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      id number url state isDraft headRefName headRefOid baseRefName
      reviewDecision mergeable mergeStateStatus
      comments(first: 100) {
        pageInfo { hasNextPage endCursor }
        nodes { id author { login } body url createdAt updatedAt }
      }
      reviews(first: 100) {
        pageInfo { hasNextPage endCursor }
        nodes { id author { login } body url state submittedAt updatedAt commit { oid } }
      }
      reviewThreads(first: 20) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved isOutdated path line
          comments(first: 100) {
            pageInfo { hasNextPage endCursor }
            nodes { id author { login } body url createdAt updatedAt }
          }
        }
      }
    }
  }
}
```

Follow **every** `hasNextPage` using a focused query with `after: endCursor`, including replies
within each thread. Top-level CLI pagination does not paginate nested connections. Combining
100 PRs, 100 threads, and 100 comments in one query exceeds GitHub's node budget; use per-PR
queries or smaller batches. If a scan is incomplete, leave its checkpoint and merge gate pending.

Store IDs, timestamps, review state, and pending actions rather than relying on a single
`updatedAt` watermark. A pending review is not a submitted approval. An outdated thread is not
automatically resolved. An informational bot comment does not require a worker.

After a worker finishes, verify the pushed SHA, changed diff, relevant check results, replies,
and resolution state. A successful local `git verify-commit` or GitHub commit verification can
confirm the signature; an inaccessible GPG home is a verification failure to diagnose, not proof
that the commit is unsigned.

## Merge PRs, including stacks

First confirm that all parent PRs are merged and the candidate targets the intended integration
branch. GitHub's asynchronous API can include open downstack PRs, so do not use a child request
as a shortcut around checking each parent's approval and feedback.

For an ordinary PR, use a supported merge tool with expected-head protection or:

```text
gh pr merge NUMBER --repo bryant-finney/budge --merge --match-head-commit HEAD_SHA
```

If GitHub reports that the PR requires its asynchronous merge REST API, use the
[documented asynchronous operation](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request-asynchronously).
The CLI command below uses typed booleans and an explicit head guard:

```text
gh api --method PUT repos/bryant-finney/budge/pulls/NUMBER/merge-async -H "X-GitHub-Api-Version: 2026-03-10" -f sha=HEAD_SHA -f merge_method=merge -f merge_action=direct_merge -F bypass_rules=false
```

Keep the returned UUID and poll the result:

```text
gh api repos/bryant-finney/budge/pulls/NUMBER/merge-async/UUID -H "X-GitHub-Api-Version: 2026-03-10"
gh pr view NUMBER --repo bryant-finney/budge --json state,mergedAt,mergeCommit
```

`pending` and `enqueued` do not mean merged. A `409` can identify an existing asynchronous
request; inspect its expected SHA and merge options before adopting it rather than submitting
duplicates. Wait interruptibly while
pending. On `failed`, report the reason and re-evaluate after the blocking state changes. An
ambiguous response must be checked before retrying a mutation. Confirm `state: MERGED` and a
merge commit before marking the PR complete; refresh each child's base, diff, checks, and
approvals after its parent merges.
