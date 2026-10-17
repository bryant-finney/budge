# budge — Design Spec

- **Date:** 2026-10-11 (rev 3: 2026-10-17, second review)
- **Status:** Draft for review
- **Author:** Bryant Finney (with Claude Code)

## 1. Purpose & success criteria

`budge` is a small, shared web app for a two-person household to see **how much
discretionary money they've spent in the trailing 7 days**, so they can make
that number part of in-the-moment purchase decisions. It is a behavior-change
feedback loop, deliberately simple and actionable.

**Success:** both users can open the app in a browser (desktop, or Chrome on
Android) and within a couple of seconds see (a) a headline "spent in the last 7
days" number and (b) a stacked day-by-day chart broken down by spending
category — reflecting real bank data that refreshes on its own, with no daily
login ("remember me", §8).

**Primary user action:** glance at the weekly number/chart before buying
something.

**One household view:** both users see the same combined number across every
linked bank, and either user can add, repair, or remove any bank. Linking an
account that is already linked is blocked (§7), so a joint account linked by
both users is normally counted once; §7 notes the one known gap where a
duplicate can slip through.

## 2. Non-goals (v1)

- No budgets/targets/limits — v1 only *reports* spend, it doesn't compare to a
  goal.
- No manual transaction re-categorization/override (auto-classification only).
- No refund/inflow netting (outflows only). A returned purchase keeps counting
  until it ages out of the 7-day window.
- No multi-currency (single-currency US household).
- No historical/trend browsing UI (we store history, but v1 renders only 7
  days).
- No Plaid webhook receiver (polling only). Plaid refreshes transactions from
  banks only a few times a day, so a scheduled poll is nearly as fresh, without
  a public, JWT-verified endpoint to secure (see §14).
- No iOS support and no native apps (v1 targets desktop browsers on
  Windows/macOS and Chrome on Android). Google sign-in on iOS Safari requires a
  redirect flow, and in-app browsers/webviews need a Plaid `redirect_uri`; both
  are deferred (§14).
- No protection against double-submits (e.g. a double tap on "link bank").
- Not more than ~two users (fixed allowlist).

## 3. Key decisions (stack)

- **Data source:** our **own** Plaid app (free Trial plan, Transactions
  product).
- **Backend API:** FastAPI (Python) on AWS Lambda (via Mangum), behind API
  Gateway HTTP API.
- **Ingestion:** separate Python Lambda on an EventBridge schedule, sharing code
  with the API.
- **Storage:** S3 (gzipped JSON per connection), behind an isolated repository
  module (DynamoDB-ready). Concurrency control via S3 conditional writes (§6).
- **Secrets:** AWS Secrets Manager (Plaid creds, session-signing key,
  per-connection access tokens).
- **Auth:** **Sign in with Google** (Google Identity Services ID-token flow) in
  the SPA, exchanged once for a **signed session cookie** issued by the API, with
  a "remember me" option (§8). Two-identity allowlist enforced in the API. No
  Cognito, no PKCE, no server-side session store.
- **Frontend:** SvelteKit 3 (`adapter-static`, SPA, **hash router**) +
  TypeScript; **Layerchart** for the chart.
- **Hosting:** S3 + CloudFront (HTTPS) on a **custom domain** — Route 53 hosted
  zone + ACM certificate (us-east-1), all managed by Pulumi.
- **IaC:** Pulumi (TypeScript).
- **Repo:** monorepo (Python backend, SvelteKit frontend, Pulumi infra); see
  §12.

## 4. Architecture

### Components

- **Frontend SPA** — SvelteKit built static, served from S3 + CloudFront over
  HTTPS. Uses SvelteKit's hash router (`router: { type: 'hash' }`), so every view is served by the single `index.html` (`#/`,
  `#/connections`) and CloudFront needs no SPA rewrites, fallback page, or
  custom error responses. Authenticates with Google, then relies on the API's
  session cookie.
- **CloudFront** — one distribution on the custom domain. *(Builder's call:)*
  serving the API on the same origin avoids CORS and needs only one
  certificate.
  - Default behavior `/*` → private SPA bucket via Origin Access Control;
    default root object `index.html`; managed `CachingOptimized` policy.
  - `/api/*` behavior → API Gateway; managed `CachingDisabled` cache policy and
    `AllViewerExceptHostHeader` origin-request policy (forwards cookies, query
    strings, and headers except `Host`, which API Gateway would reject); all
    HTTP methods allowed.
  - No custom error responses (they apply distribution-wide and would turn API
    4xx errors into HTML).
- **API Gateway HTTP API** — `$default` stage (auto-deploy), single
  `ANY /{proxy+}` route, Lambda proxy integration. CloudFront forwards the full
  `/api/...` path unchanged, and FastAPI declares its routes under an `/api`
  router prefix, so the same paths work on AWS and under local uvicorn (§12).
  Mangum needs no base-path setting.
- **API Lambda** — FastAPI. Serves the chart data, auth-session, and Plaid
  onboarding/management endpoints. Verifies the session cookie + allowlist in a
  FastAPI dependency (no gateway authorizer).
- **Ingestion Lambda** — triggered by EventBridge Scheduler (default every 4
  hours) and by async invokes from the API (`POST /sync`,
  `POST /connections/{id}/sync`, and after `POST /connections`). Pulls new
  transactions per connection and writes to S3.
- **S3** — normalized transaction store (SSE-KMS), accessed only via the
  repository module.
- **Secrets Manager** — Plaid `client_id` and per-environment `secret` (§11),
  the session-signing key, and
  each connection's `access_token`. Secret material never lands in S3.
- **Plaid** — external API: Link (browser) for onboarding; `/transactions/sync`,
  `/transactions/recurring/get` for data; `/item/remove` for teardown.
- **Pulumi (TS)** — provisions all of the above.

### Data flows

1. **Sign-in (once per device with "remember me"):** SPA → Google Identity
   Services → Google ID token → `POST /auth/session` → API verifies the token +
   allowlist → sets the `budge_session` cookie → subsequent calls carry the
   cookie automatically.
2. **Onboarding (once per bank, by the user):** SPA →
   `POST /connections/link-token` → Plaid Link opens (bank OAuth in a popup on
   desktop or a new tab on Android), user logs into the bank → Plaid returns a
   `public_token` → `POST /connections` takes the onboarding lock, rejects it if
   any selected account is already linked; otherwise exchanges it for a
   non-expiring `access_token` → stored in Secrets Manager; a `BankConnection`
   record stored in S3; an initial sync is dispatched asynchronously.
3. **Ingestion (scheduled, unattended):** EventBridge Scheduler → ingestion
   Lambda → per connection, under its lock: `/transactions/sync` from the saved
   cursor → normalize → refresh recurring ids → classify → write transactions,
   then metadata (cursor last) to S3.
4. **Read (on demand):** SPA (authenticated) → `GET /spending/weekly` → API
   computes the window in the household timezone, reads qualifying
   transactions from S3 → aggregates per day × category → returns series plus
   headline total → SPA renders the stacked chart.

```text
  Browser ──HTTPS──> CloudFront (custom domain: Route 53 + ACM)
    │                  ├─ /*     ──> S3 (static SPA, OAC)
    │                  └─ /api/* ──> API GW (HTTP API) ──> API Lambda (FastAPI)
    │                                                        ├─> S3 (data)
    │ Sign in with Google → ID token                         ├─> Secrets Manager
    ▼ (POST /api/auth/session → session cookie)              └─> Plaid API
  Google

  EventBridge Scheduler ──> Ingestion Lambda ─┬─> S3 (data)
  (+ async invoke from the API)               ├─> Secrets Manager
                                              └─> Plaid API (/transactions/sync, /recurring/get)
```

## 5. The metric: trailing-7-day discretionary spend

- **Effective date:** each transaction has
  `effective_date = authorized_date ?? date`, where both fields come straight
  from Plaid's transaction object (`YYYY-MM-DD`, no timezone):

  - `authorized_date` — "the date that the transaction was authorized"
    (nullable);
  - `date` — "for pending transactions, the date that the transaction occurred;
    for posted transactions, the date that the transaction posted."

  So a purchase lands on the day it was made, not the day it posted. The window
  **filters and buckets on `effective_date`** — the same field for both.

- **Window:** a **rolling 7 calendar days**, inclusive, ending on "today" in the
  **household timezone** — an IANA zone in Pulumi config
  (`household_timezone`, e.g. `America/Chicago`). Not UTC: a UTC window would
  roll over mid-evening for a US household. The API computes
  `end = today(household_timezone)`, `start = end - 6 days`, and includes rows
  with `start <= effective_date <= end`. The client sends no date.

- **Invariant (to the cent):**
  `total == Σ days[].total == Σ_d Σ_c days[d].by_category[c]`.

- **Included:** posted **and** pending transactions.

- **Counted amounts:** **outflows only** (spend). Refunds/inflows are **not**
  netted in v1.

- **Excluded** (via the classifier, §9; full table in Appendix A):

  - **Transfers** — primaries `TRANSFER_IN`, `TRANSFER_OUT`, and `OTHER` (Plaid
    files miscellaneous transfers under `OTHER`; see Appendix A), **except** two
    detailed values that count as spend:
    - `TRANSFER_OUT_TRANSFER_OUT_FROM_APPS` — Plaid: "money transferred out of
      the account into another application" (e.g. topping up a payment-app
      balance);
    - `TRANSFER_OUT_WITHDRAWAL` — Plaid: "withdrawals from a bank account"
      (e.g. ATM cash).
    - *Unverified:* Plaid doesn't document which category a given peer-to-peer
      service (Venmo, Zelle, Cash App) receives; a bank-to-bank payment may land
      in `TRANSFER_OUT_ACCOUNT_TRANSFER` and be excluded. Checked against real
      rows before going live (§11).
  - **Credit-card payments** — `LOAN_PAYMENTS_CREDIT_CARD_PAYMENT`.
  - **Bills** — fixed-bill categories: all `RENT_AND_UTILITIES`; all
    `LOAN_PAYMENTS` except buy-now-pay-later (`LOAN_PAYMENTS_BNPL`); and
    `GENERAL_SERVICES_INSURANCE`, `GENERAL_SERVICES_CHILDCARE`, and
    `GENERAL_SERVICES_EDUCATION`. BNPL is not excluded by category, but its
    installments usually form a Plaid recurring stream, so the recurring rule
    normally excludes them anyway; a BNPL charge counts only until Plaid
    detects its stream.
  - **Bank fees** — all `BANK_FEES`.
  - **Medical** — all `MEDICAL` (includes pharmacies and veterinary care).
  - **Taxes** — `GOVERNMENT_AND_NON_PROFIT_TAX_PAYMENT` (donations still
    count).
  - **Recurring** — any transaction whose id is in a Plaid recurring **outflow**
    stream (catches subscriptions sitting in discretionary categories).
  - **Decided:** for v1 we **trust Plaid's recurring detection as-is** — every
    outflow stream counts as a bill, whatever its frequency or category. We
    accept that Plaid may sometimes flag a habit (e.g. weekly groceries) as
    recurring and drop it from the number. Filtering streams by frequency or
    category is a v2 tuning step (§14).
  - Everything else counts, including transactions with no Plaid category
    (charted as `UNCATEGORIZED`, a name that can't collide with Plaid's own
    `OTHER` primary).

- **Amount sign:** Plaid uses positive = money out of the account. We normalize
  so **spend is positive**; only positive (outflow) amounts count.

- **Money format:** amounts stay floats in dollars, as Plaid sends them, and go
  out as JSON numbers. Aggregation uses plain `sum()`, and every figure in the
  response (`total`, each `days[].total`, each `by_category` value) is rounded
  with `round(x, 2)` just before it is returned. Every input is a whole number
  of cents, so every true sum is too; accumulated float error (~1e-13) is
  orders of magnitude below half a cent, so rounding recovers the exact value
  and the invariant holds to the cent. No `Decimal`.

## 6. Data model & storage

### Entities

**`BankConnection`** (one Plaid *Item* = one login at one institution):
`connection_id` (= Plaid `item_id`), `institution_id`, `institution_name`,
`linked_by` (the linking user's `client_user_id`), `plaid_env` (`sandbox` |
`production`, the environment it was linked in; see Environment scoping
below), `accounts` (list of
`{account_id, name, mask, type, subtype}` — used for the duplicate-account
check), `cursor` (sync cursor), `status` (`initializing` | `healthy` |
`login_required`), `transactions_update_status` (last value seen from Plaid),
`recurring_outflow_ids` (latest set from `/transactions/recurring/get`),
`created_at`, `last_synced_at`. The `access_token` is **not** stored here — it
lives in Secrets Manager keyed by `connection_id`.

**`Transaction`** (normalized): `transaction_id`, `connection_id`, `account_id`,
`date` (Plaid `date`: occurred date if pending, posted date if posted),
`authorized_date` (nullable), `effective_date` (`authorized_date ?? date`, §5), `datetime` (nullable), `amount` (float, dollars;
normalized: spend positive), `currency`, `name`, `merchant_name` (nullable), `pfc_primary`
(nullable), `pfc_detailed` (nullable; Plaid PFC **v2**), `pending` (bool),
`pending_transaction_id` (nullable), `is_discretionary` (bool),
`excluded_reason` (`inflow` | `transfer` | `cc_payment` | `bill` | `bank_fee` |
`medical` | `tax` | `recurring` | `none`). Raw category + computed flag are both
stored so exclusion rules can be retuned without re-fetching: every ingestion
run re-classifies **all** stored rows for the connection (§9).

### S3 layout

```text
connections/{connection_id}/metadata.json          # BankConnection: metadata + cursor + status
connections/{connection_id}/transactions.json.gz   # normalized transactions
locks/connection-{connection_id}.json              # per-connection lease
locks/onboarding.json                              # global lease for link/duplicate check
```

One object per connection (not one per transaction). On sync: read the object,
apply the folded deltas (§7), write back. Month-partitioning is a future scaling
step, not v1.

### Concurrency: leases via S3 conditional writes

S3 supports atomic conditional writes on `PutObject` (SigV4-signed, the boto3
default): `If-None-Match: *` creates an object only if the key doesn't exist,
and `If-Match: <etag>` overwrites only if the object is unchanged; a losing
writer gets `412 Precondition Failed` (or `409 ConditionalRequestConflict`
during a concurrent write — retry). `DeleteObject` supports `If-Match` too
(conditional deletes). See
<https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-requests.html>.

- **Lease object:** `{owner, acquired_at, expires_at}`; `owner` is a random
  UUID per acquisition.
- **Acquire:** `PutObject` with `If-None-Match: *`. On 412, read the lease; if
  `expires_at` has passed, **take over** with `PutObject` `If-Match: <etag>`;
  otherwise the lease is held.
- **Release:** `DeleteObject` with `If-Match: <etag>` of our own write, so we
  never delete someone else's lease.
- **TTL:** longer than the longest holder (ingestion Lambda timeout, 10 min) —
  15 min.
- **Coverage:** **every** mutation of a connection's objects holds its
  `connection-{id}` lease: ingestion, onboarding writes, repair-triggered sync,
  and `DELETE` (so an in-flight sync can't re-create deleted data).
  `POST /connections` holds the `onboarding` lease across the duplicate check,
  token exchange, and initial save, so two users linking at once can't both
  pass the check.
- **Write order** within a sync: `transactions.json.gz` first, then one
  `metadata.json` write (cursor, status, `last_synced_at`, recurring ids). A
  crash in between replays the same deltas next run, which is idempotent (§7).

### Repository boundary

A Python `Repository` protocol the rest of the app depends on; an S3
implementation now, a DynamoDB implementation later satisfying the same
interface. The protocols live in `storage/`; every AWS-backed implementation
lives in the `budge.aws` adapter package (`aws/`): the S3 `Repository`, the
Secrets Manager `SecretStore`, and the Lambda async-invoke
`IngestionTrigger` the API uses to start ingestion (§7, §12; protocol in
`ingestion/`). No module outside `aws/` imports `boto3`, and the rest of the
app depends only on the protocols, so tests substitute fakes.

- `list_connections()`, `get_connection(id)`, `save_connection(c)`,
  `delete_connection(id)` (metadata + transactions)
- `get_transaction_rows(connection_id)`,
  `put_transaction_rows(connection_id, rows)`,
  `get_transactions(start, end, discretionary_only=True)` (inclusive range on
  `effective_date`, across all connections)
- `lock(name)` — a **context manager** implementing the lease above
  (acquire/release, release-on-exception, stale-lease takeover); raises
  `LeaseHeld` if it can't acquire.

**Environment scoping:** the repository is constructed with the current
`plaid_env`, and `list_connections()`, `get_connection(id)`, and
`get_transactions(...)` see only connections linked in that environment. So
ingestion, `GET /connections`, and `GET /spending/weekly` all ignore the other
environment's records. After switching from `sandbox` to `production` (§11),
the Sandbox connections, tokens, and transactions stay in S3 and Secrets
Manager untouched but invisible; remove them by hand if wanted.

Secrets are a **separate** module: `SecretStore.get_access_token(connection_id)`
/ `put_access_token(connection_id, token)` /
`delete_access_token(connection_id)` over Secrets Manager — so nothing in the
transaction path can touch token material.

## 7. Plaid integration

Verified against current Plaid docs (2026-10-17). Flow uses the Transactions
product.

### Onboarding

- **`POST /connections/link-token`** mints a `link_token` via
  `/link/token/create` with: `client_name`, `language`, `country_codes`,
  **`products: ["transactions"]`** (required or sync stays empty),
  **`user.client_user_id`** (see strategy below), and
  **`transactions.days_requested`** (request the max, 730, to seed history
  cheaply; it applies only when an Item is first created). **No
  `redirect_uri` in v1:** Plaid documents it as optional for desktop and mobile
  web — the bank's OAuth page opens in a popup (desktop) or a new tab (Android)
  and returns to Link. It is only required for webviews/in-app browsers, which
  are out of scope (§2). No `webhook` in v1 (it is fixed at Item creation; v2
  can set it with `/item/webhook/update`).

- **Account selection:** Link must let users pick accounts — enable
  multi-select in the Plaid Dashboard's Link customization (§11). At OAuth banks
  the bank's own account picker is used instead.

- **Duplicate-account block (decided):** Plaid does **not** prevent duplicate
  Items; its docs ask the app to check before exchanging the token. Each real
  account may be linked only once. The SPA sends Link's `onSuccess` metadata
  (`institution.institution_id` and the selected `accounts` with `name`,
  `mask`, `type`, `subtype`) along with the `public_token`. Under the
  `onboarding` lease, an account is a duplicate if an existing connection with
  the same `institution_id` has an account with the same `name` **and**
  `mask` — Plaid's documented rule. When `name` or `mask` is null, fall back to
  Plaid's Item-level rule: same `institution_id` linked by the same
  `client_user_id`. (Known gap: a joint account with a null mask linked by the
  *other* user is not caught.) Never treat `mask` as an account number. If
  **any** selected account is a duplicate, `POST /connections` returns
  `409 duplicate_account` naming it, **without** exchanging the token (an
  unexchanged `public_token` simply expires). The SPA tells the user to link
  again and deselect that account.

- **`POST /connections`**, under the `onboarding` lease, in this order:

  1. the duplicate-account check (above);
  2. exchange the `public_token` via `/item/public_token/exchange` →
     `access_token` (non-expiring) + `item_id`;
  3. store the `access_token` in Secrets Manager;
  4. save the `BankConnection` to S3 (`connection_id` = `item_id`, current
     `plaid_env`, `status = initializing`);
  5. **async-invoke** the ingestion Lambda for that one connection (API
     Gateway's 30 s timeout rules out a synchronous sync).

  **A failure after step 2 unlinks the Item**, via a context manager entered
  right after the exchange and wrapping steps 3–4:

  ```python
  with unlink_on_failure(plaid, secrets, item_id, access_token):
      secrets.put_access_token(item_id, access_token)  # step 3
      repo.save_connection(connection)  # step 4
  invoke_ingestion(item_id)  # step 5, outside the block
  ```

  If the block raises, `__exit__` calls `/item/remove` with the `access_token`
  still in hand, deletes the secret (a missing secret is a no-op), and
  re-raises, so the route returns its error (`502 plaid_error` or
  `500 internal_error`) and no orphaned Item is left at Plaid. If the cleanup
  itself fails, it logs the `item_id` at error level for manual removal and
  still re-raises the original error. A failed step 5 is **not** a link
  failure: the connection is saved and the next scheduled run syncs it.
  Returns `201` with the connection; the SPA polls `GET /connections` for
  progress.

- **`client_user_id` strategy:** `UUIDv5(fixed_namespace, google_sub)` — stable,
  non-PII, and derived on the fly, so no user→UUID table is stored. No
  `/user/create` (that's for Income/CRA products only).

### Sync (`/transactions/sync`)

- Always pass `count: 500` (the max; default is 100) and
  `options.personal_finance_category_version: "v2"`.
- Cursor loop: first call `cursor = null`; while `has_more`, accumulate pages,
  advance `next_cursor`; **persist the cursor only after the loop ends**. The
  final cursor is valid ≥ 1 year.
- **Delta folding:** fold all pages, in page order, into one map
  `{transaction_id: row | REMOVED}`, then apply that final state to the stored
  rows. (The same id can be added on one page and removed on a later one;
  applying all removes then all adds would resurrect it.) Removing an unknown
  id is a no-op, so replaying deltas after a crash is idempotent.
- **Pending → posted:** Plaid sends the pending id in `removed` plus the posted
  transaction in `added` (new id, `pending_transaction_id` set). As a
  safeguard, when a posted row arrives whose `pending_transaction_id` is still
  stored, drop that pending row.
- **Initial-sync delay:** right after linking, sync can return empty arrays +
  empty cursor meaning "not ready." Gate on `transactions_update_status`:
  - `NOT_READY` → leave the cursor untouched; status stays `initializing`;
    outcome `not_ready`. Only a **single-connection run invoked from the API**
    (after `POST /connections` or a repair) waits for it, retrying with capped
    backoff (total ≤ 2 min, inside the Lambda timeout). Scheduled and
    all-connection runs check once and move on, so a new bank can't hold up
    the others; the next scheduled run tries again (scheduled runs process
    `initializing` connections).
  - `INITIAL_UPDATE_COMPLETE` / `HISTORICAL_UPDATE_COMPLETE` → proceed; status
    `healthy`.
- **Mutation during pagination** (`TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION`
  or any mid-loop error): restart the loop from the first page's cursor, at
  most **3 restarts** per run; after that the connection's outcome is `error`
  and the next run tries again. Never retry a single page, never persist a
  mid-loop cursor.
- **`ITEM_LOGIN_REQUIRED`** surfaces as the sync error (and in `/item/get`
  `item.error`): set the connection `status = login_required`, stop, don't
  advance the cursor. Surfaced via `GET /connections`.
- Other Plaid error codes are handled at implementation time (branch on
  `error_code`, not HTTP status).

### Recurring exclusion

- Once `transactions_update_status` is `HISTORICAL_UPDATE_COMPLETE`, **every**
  run calls `/transactions/recurring/get` (`access_token`,
  `options.personal_finance_category_version: "v2"`) → collects
  `outflow_streams[].transaction_ids` → stores them as the connection's
  `recurring_outflow_ids` → the classifier re-runs over all stored rows. If the
  call fails, keep the last-known ids and don't fail the sync. (Assumed
  available on our plan — see §11.)
- **Known v1 lag (accepted):** a recurring charge can count as discretionary for
  a while and then drop out of the number:
  - before `HISTORICAL_UPDATE_COMPLETE` (no stream data yet);
  - while it is **pending** (stream `transaction_ids` cover posted
    transactions);
  - between runs, until Plaid's stream picks up the new charge.

### Teardown & repair

- **`DELETE /connections/{id}`** (under the connection lease), in this order,
  each step idempotent:

  1. `/item/remove` with the stored `access_token` (`ITEM_NOT_FOUND` counts as
     success); skipped if the secret is already gone, since the secret is only
     deleted after a successful removal;
  2. delete `transactions.json.gz`;
  3. delete the secret (a missing secret counts as done);
  4. delete `metadata.json` **last**.

  No rollback: `/item/remove` can't be undone, so a failure simply stops and
  returns the error. Because the metadata goes last, the connection stays
  listed (and `DELETE` stays reachable instead of returning `404`) until every
  step has succeeded, so a retry finishes the job.

- **`POST /connections/{id}/link-token`** → `/link/token/create` with the
  existing `access_token` and `user.client_user_id` (update mode, omit
  `products`). After the user completes update-mode Link, the original
  `access_token` resumes — **do not** re-exchange. The SPA then calls
  `POST /connections/{id}/sync`, which sets `status = initializing` and
  async-invokes ingestion for that connection; a successful sync sets
  `healthy`.

## 8. API contract

All routes are served under `/api` on the app's domain (via CloudFront, §4).
Every request and response body is a Pydantic model, so FastAPI's generated
OpenAPI document is the complete contract (milestone 2, §13); the shapes below
are normative.

### Auth

- **Sign-in:** the SPA obtains a Google ID token from Google Identity Services
  (button / One Tap) and posts it to `POST /auth/session`. The API verifies it:
  signature against Google's JWKS (cached at Lambda module scope), `iss` ∈
  {`accounts.google.com`, `https://accounts.google.com`}, `aud` == our client
  ID, `exp` (with ~10 s leeway). It then checks the **allowlist of Google
  `sub` values** (Pulumi config). Bootstrap: a rejected sign-in logs its `sub`
  so it can be added to config.
- **Session cookie:** on success the API sets `budge_session` = an HS256 JWT
  `{sub, iat, exp}` signed with a key in Secrets Manager (generated by
  Pulumi). Attributes: `HttpOnly; Secure; SameSite=Strict; Path=/api`.
  - **Remember me checked:** `exp` = 30 days and `Max-Age` = 30 days.
  - **Unchecked:** browser-session cookie (no `Max-Age`), `exp` = 12 hours.
- **Every request** except `POST /auth/session` and `GET /health` requires a
  valid cookie; the dependency verifies signature + `exp` and re-checks `sub`
  against the allowlist (so removing a `sub` from config revokes access).
  Rotating the signing key signs everyone out.
- **CSRF:** `SameSite=Strict` plus same-origin hosting is sufficient for v1;
  mutating routes also require `Content-Type: application/json`.
- **Status codes:** `401 unauthenticated` (missing/invalid/expired cookie or
  Google token) → SPA shows sign-in. `403 not_allowlisted` (valid identity, not
  on the list) → SPA shows "not authorized" and calls
  `google.accounts.id.disableAutoSelect()` (avoids an auto-sign-in loop).

### Routes

| Method & path                       | Request                                                                                            | Success                                               |
| ----------------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `POST /auth/session`                | `{credential, remember_me}`                                                                        | `204`, sets cookie                                    |
| `DELETE /auth/session`              | —                                                                                                  | `204`, clears cookie (sign-out)                       |
| `GET /spending/weekly`              | —                                                                                                  | `200` weekly response (below)                         |
| `POST /connections/link-token`      | —                                                                                                  | `200 {link_token, expiration}`                        |
| `POST /connections`                 | `{public_token, institution: {institution_id, name}, accounts: [{id, name, mask, type, subtype}]}` | `201 {connection}`                                    |
| `GET /connections`                  | —                                                                                                  | `200 {connections: [connection]}`                     |
| `POST /connections/{id}/link-token` | —                                                                                                  | `200 {link_token, expiration}` (update mode)          |
| `POST /connections/{id}/sync`       | —                                                                                                  | `202 {accepted: true}` (after repair)                 |
| `DELETE /connections/{id}`          | —                                                                                                  | `204` (idempotent)                                    |
| `POST /sync`                        | —                                                                                                  | `202 {accepted: true}` (all connections)              |
| `GET /health`                       | —                                                                                                  | `200 {ok: true}` (unauthenticated; deploy smoke test) |

`connection` =
`{connection_id, institution_name, accounts: [{account_id, name, mask, type, subtype}], status, last_synced_at, created_at}`.

`POST /sync` and `POST /connections/{id}/sync` **async-invoke** the ingestion
Lambda and return immediately; the SPA learns the outcome by polling
`GET /connections` (`status`, `last_synced_at`). Neither forces the bank to
refresh — Plaid checks banks 1–4 times a day, and forcing a check
(`/transactions/refresh`) is billed separately and not used. UI copy should say
"check for new transactions", not "refresh from bank".

**`GET /spending/weekly` response:**

```jsonc
{
  "window": { "start": "2026-10-05", "end": "2026-10-11" },   // 7 days inclusive, household timezone
  "currency": "USD",
  "total": 437.21,
  "categories": ["FOOD_AND_DRINK", "GENERAL_MERCHANDISE", "TRANSPORTATION"],
  "days": [
    { "date": "2026-10-05", "total": 52.10,
      "by_category": { "FOOD_AND_DRINK": 40.00, "GENERAL_MERCHANDISE": 12.10 } }
    // exactly 7 entries, zero-filled for days with no spend
  ]
}
```

- `categories` lists `pfc_primary` keys (or `UNCATEGORIZED`) with a non-zero
  window
  total, ordered by window total descending, then name.
- `by_category` omits zero entries.

### Errors

One envelope for **every** error, including FastAPI's request-validation errors
(a custom handler replaces the default `422 {"detail": [...]}`):
`{ "error": { "code": "<enum>", "message": "<human text>" } }`.

| HTTP  | `code`                                                                  |
| ----- | ----------------------------------------------------------------------- |
| `401` | `unauthenticated`                                                       |
| `403` | `not_allowlisted`                                                       |
| `404` | `not_found` (unknown connection)                                        |
| `409` | `duplicate_account` (§7), `lease_held` (connection busy; retry shortly) |
| `422` | `invalid_request`                                                       |
| `502` | `plaid_error` (Plaid upstream failure)                                  |
| `500` | `internal_error`                                                        |

`DELETE` is destructive; the SPA confirms before calling it.

## 9. Ingestion & exclusion logic

- **Triggers → one shared `run_ingestion(connection_ids=None)`:** EventBridge
  Scheduler (all connections) and the API's async invokes (all, or one
  connection) all call it. Each connection is processed inside
  `with repo.lock(f"connection-{id}"):` and its own try/except, so one failure
  never aborts the others; a connection whose lease is held is skipped (the
  holder is already syncing it).

- **Retries:** the ingestion Lambda's async-invoke config sets
  `MaximumRetryAttempts = 0`, and the Scheduler target's retry policy is 0 —
  the next scheduled run is the retry. This only avoids redundant work: Lambda
  async delivery is at-least-once, so the per-connection lease (§6) is what
  keeps two runs from syncing the same connection at once.

- **Run summary** (returned and logged as one JSON line):
  `{connection_id: {outcome, added, modified, removed, error_code}}` with
  `outcome` ∈ `ok` | `skipped_locked` | `not_ready` | `login_required` |
  `error`.

- **Systemic failure** — Plaid credentials invalid (`INVALID_API_KEYS`), S3 or
  Secrets Manager inaccessible, or every connection failing with the same
  non-Item error — makes the Lambda raise (so the CloudWatch error alarm fires,
  §12). Per-connection failures are logged + summarized and the Lambda returns
  success.

- **Per connection:** load metadata + access token → run the sync loop (§7) →
  normalize + fold deltas into the stored rows → if historical-complete,
  refresh recurring outflow ids → classify **all** stored rows → write
  transactions, then metadata (cursor, status, `last_synced_at`, recurring
  ids).

- **Exclusion classifier — a pure function**, no I/O, exhaustively unit-tested
  with golden input→output rows:
  `classify(transaction, recurring_outflow_ids) -> (is_discretionary, excluded_reason)`.
  The PFC mapping is a pinned data table, `PFC_RULES` (Appendix A), retunable
  without re-fetching (the next run re-classifies stored rows). Each key is a
  full PFC v2 value (primary or detailed) and maps to either an
  `excluded_reason` or the sentinel `COUNT`. The algorithm is normative:

  ```python
  COUNT = "count"  # ends the PFC lookup as "spend"; the recurring check still applies


  def classify(txn, recurring_outflow_ids):
      if txn.amount <= 0:
          return False, "inflow"
      verdict = None
      if txn.pfc_detailed is not None:
          verdict = PFC_RULES.get(txn.pfc_detailed)  # a detailed entry wins...
      if verdict is None and txn.pfc_primary is not None:
          verdict = PFC_RULES.get(txn.pfc_primary)  # ...else fall back to primary
      if verdict is not None and verdict != COUNT:
          return False, verdict
      if txn.transaction_id in recurring_outflow_ids:
          return False, "recurring"
      return True, "none"
  ```

  So a PFC exclusion beats the recurring rule (a credit-card payment that also
  matches a recurring stream reads as `cc_payment`), and a `COUNT` row (e.g.
  `LOAN_PAYMENTS_BNPL`) can still be excluded as `recurring`.

## 10. Frontend

- **SvelteKit** with `adapter-static` (SPA) and the **hash router** → pure
  static files to S3 + CloudFront. The hash router renders entirely in the
  browser, so page options (`ssr`, `prerender`, `trailingSlash`) are not set;
  SvelteKit 3 rejects them (`router_hash_page_options`). All in-app links start
  with `#/`. TypeScript throughout.
- **Configuration (SvelteKit 3):** SvelteKit 3 no longer reads
  `svelte.config.js`; the options formerly under `config.kit` are passed
  directly to the `sveltekit()` Vite plugin in `vite.config.ts`, e.g.
  `sveltekit({ files: { src: '.' }, router: { type: 'hash' }, adapter: adapter({ fallback: 'index.html' }) })`.
- **Layout (flat, no nested `src/`):** `files.src: '.'` puts `routes/`,
  `app.html`, and `app.d.ts` directly under `src/front-end/`, mirroring the
  back end's `src/back-end/budge/`. Shared code lives in `src/front-end/lib/`,
  imported as `#lib` via the package's `imports` field (SvelteKit 3 removed
  `$lib`). If `files.src: '.'` proves unworkable (e.g. the tooling scans
  `node_modules/` or build output), fall back to a non-`src` directory such
  as `src/front-end/app/`.
- **Supported browsers (v1):** current Chrome, Edge, Firefox, and Safari on
  Windows/macOS; Chrome on Android. No iOS (§2).
- **Views:** `#/` — the weekly chart + headline total; `#/connections` — list /
  add / repair / remove banks; sign-in (shown whenever the API returns `401`).
- **Data:** essentially one call, `GET /spending/weekly` (no client date; the
  API owns the window, §5).
- **Chart:** **Layerchart** (pin the major version) stacked bar/area — day
  buckets on x, category series stacked. Palette, stack order, legend, and
  accessibility follow the `dataviz` skill at build time (deferred
  deliberately; not specified here).
- **Auth:** Google Identity Services "Sign in with Google" button (popup mode),
  plus a **"Remember me" checkbox** sent as `remember_me` to
  `POST /auth/session`. The Google ID token is used once and discarded; the
  SPA never stores credentials (the session cookie is `HttpOnly`). Sign-out
  calls `DELETE /auth/session`.
- **Plaid Link:** loaded from `cdn.plaid.com`; no redirect handling (no
  `redirect_uri`, §7). After update-mode `onSuccess`, call
  `POST /connections/{id}/sync`; after `POST /connections`, poll
  `GET /connections` until the new connection leaves `initializing`.
- UI states (empty, loading, initializing, `login_required`, stale data,
  errors) are designed at implementation time.

## 11. Plaid access — Sandbox first (user-owned checks)

The Plaid account is brand new and unverified, so assume **no live access
yet**. The build is **Sandbox-first**: everything is built and proven
end-to-end against Plaid Sandbox, and a `plaid_env` setting (`sandbox` |
`production`) switches environments with no code changes. Connections are
tagged with the environment they were linked in (§6), so Sandbox data never
mixes into the real number. Plaid's `secret` differs per environment (the
`client_id` is shared), so Secrets Manager holds one per environment and the
app reads the one matching `plaid_env`. Going live is a user-owned gate before
real data, not a blocker for the build:

- **The Trial plan is the live path.** It connects real banks with real
  Production data. **Do not file a Production-access application:** per Plaid,
  a team with a pending or approved Production application can't use (or
  return to) the Trial plan
  (<https://support.plaid.com/hc/en-us/articles/39994173227159-What-is-the-Plaid-Trial-plan>).
  Revisit only if Trial's limits are outgrown.
- Before trusting the number, spot-check Appendix A against real transactions
  — in particular which categories peer-to-peer payments (Venmo, Zelle, Cash
  App) and payment-app top-ups receive (§5).
- Confirm **`/transactions/recurring/get`** is accessible on the plan (it is a
  documented add-on; v1 assumes it is available — if not, fall back to
  category-only exclusion).
- In the Plaid Dashboard's Link customization, set account selection to
  **multi-select** (not "require all"), so users can deselect already-linked
  accounts (§7).
- Complete any per-bank OAuth registration Plaid requires. Most large US banks
  use OAuth. No `redirect_uri` registration is needed in v1 (§7).

## 12. Repository, tooling, testing, deployment, observability

### Repository & tooling

Versions and tools below are the *builder's call*; adjust at milestone 1.

```text
src/
  back-end/       # uv project: budge package (api/, aws/, ingestion/, storage/, plaid_client/, classify/), tests/, Dockerfile
  front-end/      # SvelteKit app (pnpm)
  infrastructure/ # Pulumi TypeScript program (pnpm)
docs/
.github/workflows/
```

- **Python:** version-agnostic across every actively supported CPython
  (not past end-of-life on python.org; at time of writing 3.11–3.15, with 3.10
  reaching end-of-life this month). `requires-python` is the oldest supported
  version and is raised as versions reach end-of-life; CI tests the full
  version matrix. The Lambdas run on the **newest generally available Lambda
  Python runtime** (base image `public.ecr.aws/lambda/python:3.14` today;
  `python3.15` is in Lambda public preview only, not for production). Managed
  with **uv**; **ruff** (lint + format), **mypy** (strict), **pyright** (strict),
  **pytest** (+ moto, coverage).
- **TypeScript:** Node 24 LTS, **pnpm** workspace (`front-end`, `infrastructure`);
  **eslint**, **prettier**, **svelte-check**, **Vitest** + Svelte Testing
  Library.
- **pre-commit:** the existing generic, mdformat, markdownlint-cli2, gitleaks
  (secret scanning), yamllint, and taplo hooks, plus ruff, mypy, pyright,
  eslint, prettier, and svelte-check. Every lint, format, and static-analysis
  check that CI/CD runs has a local parallel, via `pre-commit` where possible.
- **Local dev:** `.envrc` copies the template `etc/base.env` to `.env` on first
  use and loads it with direnv's `dotenv_if_exists`. `.env` (git-ignored) holds
  `PLAID_CLIENT_ID`, `PLAID_CLIENT_SECRET`, `PLAID_ENV` (Plaid Sandbox creds),
  `AWS_PROFILE`, and `PULUMI_BACKEND_URL` — **never** local endpoint
  overrides, which would leak into `aws` and `pulumi up` commands run from the
  same shell. One
  `docker compose up` runs the stack from the **same backend image** that is
  deployed; no AWS account, no SAM, and no second IaC template:
  - **`api` service:** the backend image with its entrypoint overridden to run
    the FastAPI ASGI app under **uvicorn**. API Gateway and Mangum are not
    emulated: on AWS they only translate an HTTP request into an event and back
    for this same ASGI app. Routes carry the `/api` prefix in FastAPI itself
    (§4), so paths are identical locally and on AWS.
  - **`ingestion` service:** the backend image with its default Lambda
    entrypoint. Outside Lambda, AWS's Python base images start the bundled
    **Runtime Interface Emulator**, which serves the Lambda Invoke API path
    (`/2015-03-31/functions/function/invocations`). The API's boto3 Lambda
    client reaches it through `AWS_ENDPOINT_URL_LAMBDA`, so the real
    invoke code path runs locally. The function name is configuration
    (`function` locally, the real ARN on AWS). The emulator may not honor
    `InvocationType=Event` (async); verify at milestone 2. If it doesn't, the
    local call blocks until ingestion finishes, which is acceptable for
    development.
  - **`minio` service (S3):** implements the
    conditional `PutObject` headers the lease relies on (§6), so the lease
    behaves locally as it does on AWS; verify conditional `DeleteObject`
    (`If-Match`) at milestone 2, and if it's missing, the local lease release
    falls back to an unconditional delete after re-reading the owner. Bucket
    default encryption (SSE-KMS) is an AWS-side setting; the repository never
    sends per-request encryption headers, so the same code runs against both.
    Pin the image tag (MinIO's community edition is source-only/maintenance
    mode, so published images are not updated).
  - **`moto` service (Secrets Manager):** moto server, seeded with the Plaid
    Sandbox creds and a session-signing key at startup.
  - **Wiring:** service-specific endpoint env vars, set **only** in each
    compose service's `environment:` block and honored natively by boto3:
    `AWS_ENDPOINT_URL_S3` → MinIO, `AWS_ENDPOINT_URL_SECRETS_MANAGER` → moto,
    `AWS_ENDPOINT_URL_LAMBDA` → the `ingestion` service. The schedule isn't
    emulated; trigger ingestion with `POST /api/sync`, or by invoking the
    emulator directly with `curl`.
  - **Frontend:** the Vite dev server proxies `/api` to the `api` service, so
    there's no CORS. `http://localhost:<vite port>` is added to the Google
    OAuth client's authorized JavaScript origins.
  - **Gap, covered by tests:** API Gateway's event format and Mangum's
    translation (path, query string, cookies, headers) don't run locally. Unit
    tests drive the Mangum handler with recorded API Gateway HTTP API payload
    v2 fixtures (§12 Testing), and the deploy smoke test calls
    `GET /api/health` through CloudFront.

### Testing

- Exclusion classifier: the PFC v2 taxonomy CSV is checked in
  (`classify/pfc-taxonomy-v2.csv`). A golden test enumerates **every** detailed
  value in it and asserts its expected verdict; another asserts every
  `PFC_RULES` key appears in the CSV (catches typos and Plaid renames).
- Pure unit (TDD): classifier edge cases (null PFC, `COUNT` + recurring),
  trailing-7 day×category
  aggregation (window edges, household timezone, `effective_date`, the total
  invariant compared in cents via `round(x * 100)`, response figures rounded
  to 2 places with no float noise such as `437.21000000000004`), sign
  normalization, delta folding.
- Repository: S3 impl against **moto** — gzip round-trip, write order, and the
  lease (acquire/release, release-on-exception, stale takeover, contention).
  **Risk:** confirm moto honors `If-None-Match`/`If-Match` on `PutObject` and
  `DeleteObject`; if not, run the lease tests against the MinIO container
  (marked as integration tests).
- Plaid client/sync loop: mocked Sandbox fixtures — `has_more` pagination,
  mutation-restart, `NOT_READY`, `ITEM_LOGIN_REQUIRED`, pending→posted.
- API: FastAPI `TestClient` with a fake repository — routes, error envelope
  (including validation errors), session cookie issue/verify/expiry,
  `401` vs `403`, Google-token verification against a self-signed JWKS fixture
  (bad `aud`/`iss`, expired), duplicate-account `409`, weekly response shape,
  and onboarding rollback (a failed secret or S3 write calls `/item/remove`,
  deletes the secret, and re-raises).
- Lambda handlers: the Mangum-wrapped API handler driven with recorded API
  Gateway HTTP API payload v2 events (path with `/api`, query string, cookies
  in, `Set-Cookie` out), since local dev bypasses API Gateway; the ingestion
  handler with Scheduler and async-invoke payloads.
- Integration (CI-gated): real Plaid **Sandbox** create/exchange/sync (via
  `/sandbox/public_token/create`) → assert rows land in S3.
- Frontend: Vitest + Svelte Testing Library — chart-data mapping, auth guard,
  remember-me submission.

### Deployment (Pulumi/TS)

- **Stack & state:** single `prod` stack, pointed at Plaid Sandbox until live
  access is granted (§11). Region `us-east-1` (matches CloudFront's
  certificate region, so one AWS provider suffices).
- **Pulumi state on AWS (no Pulumi Cloud):** self-managed **S3 backend**
  (`PULUMI_BACKEND_URL=s3://budge-pulumi-state-<account_id>?region=us-east-1`)
  with a **KMS secrets provider**
  (`pulumi stack init prod --secrets-provider "awskms://alias/budge-pulumi-secrets?region=us-east-1"`).
  The state bucket (versioning on, Block Public Access, SSE) and KMS key can't
  be managed by the stack whose state they hold, so a one-time, idempotent
  `src/infrastructure/bootstrap.sh` (AWS CLI) creates them, along with the GitHub OIDC
  provider and deploy role. Pulumi's S3 backend writes its own lock files, so
  concurrent `pulumi up` runs are refused.
- **Config:** non-secret settings in Pulumi config — domain name,
  `household_timezone`, Google client ID, allowlisted Google `sub`s,
  `plaid_env`, schedule rate (default `rate(4 hours)`), `days_requested`.
  Plaid creds seeded into Secrets Manager out-of-band (one `secret` per Plaid
  environment, §11); the session-signing key
  is generated by Pulumi (`random`) into Secrets Manager.
- **DNS & TLS:** Route 53 hosted zone + records; ACM certificate
  (DNS-validated). The domain is registered out-of-band. If it's registered
  outside Route 53, the first deploy is two-phase: create the zone, delegate
  its nameservers at the registrar, then deploy the certificate and
  distribution (validation blocks until delegation works). If it's registered
  with Route 53 Domains, look up the auto-created zone instead.
- **Storage:** data bucket (SSE-KMS, Block Public Access, versioning) and SPA
  bucket (private, OAC).
- **Compute:** one ECR repository (lifecycle: keep the last 10 images); one
  backend image built by `@pulumi/docker-build` for **`linux/arm64`** (Graviton
  Lambdas; also native on Apple Silicon) and used by both functions with
  different handlers. API Lambda: 1024 MB, 29 s timeout. Ingestion Lambda:
  1024 MB, 10 min timeout, async retries 0.
- **API Gateway** HTTP API (`$default` stage, default-route throttling, e.g.
  10 rps / burst 20); **CloudFront** as in §4; **EventBridge Scheduler**
  schedule → ingestion Lambda.
- **IAM:** least privilege (ingestion: read secrets + rw data; API: rw data +
  read/write/delete connection secrets + read session key + async-invoke
  ingestion). Exact policies at implementation time.
- **Frontend deploy:** `vite build` output synced to the SPA bucket (Pulumi
  `synced-folder` or `aws s3 sync` in CI); hashed assets
  `Cache-Control: max-age=31536000, immutable`, `index.html`
  `Cache-Control: no-cache`; CloudFront invalidation of `/index.html` after
  each deploy.
- **CI/CD (GitHub Actions):** on pull requests — pre-commit, type checks, and
  both test suites. On `main` — build the image, `pulumi up`, deploy the
  frontend, smoke-test `GET /api/health`. AWS access via a GitHub OIDC role
  (no long-lived keys); the same role grants access to the Pulumi state
  bucket and secrets KMS key, so no Pulumi token is needed.

### Observability (minimal, CloudWatch)

- Structured JSON logs to CloudWatch Logs, 30-day retention; the ingestion run
  summary logged each run.
- CloudWatch alarms → one SNS topic with email subscriptions:
  - ingestion Lambda `Errors` > 0 (systemic failure, §9);
  - API Lambda `Errors` > 0 over 5 min;
  - a metric filter on the run summary counting connections with `outcome` ∈
    {`error`, `login_required`} > 0.

## 13. Milestones

In order; each ends with its checks green in CI (or locally before milestone
5).

1. **Monorepo skeleton** — layout per §12; static analysis, linting, and
   formatting for Python and TypeScript; `pre-commit`; CI/CD scaffolding; test
   suites that exercise the skeleton code.
2. **Back end works locally** — `docker compose up` runs the backend image
   (API under uvicorn, ingestion under the Lambda Runtime Interface Emulator)
   with MinIO (S3) and moto server (Secrets Manager), per §12; Google sign-in → session cookie works locally; all back-end
   tests pass; FastAPI's built-in OpenAPI document is complete, with every
   route, model, and error documented (it is the API contract). IaC not yet in
   scope.
3. **Front end works locally** — a user can sign in and link a Sandbox bank
   against the local back end, and see the weekly chart.
4. **IaC works locally** — `pulumi up` from a laptop provisions the cloud
   infrastructure and deploys the back end and front end.
5. **GitHub Actions CI/CD** — workflows run all tests and deployments
   successfully.

## 14. Future (v2+)

- Plaid **webhook receiver** (`POST /webhooks/plaid`, JWT-verified) for
  `PENDING_DISCONNECT`, permission revocation, `LOGIN_REPAIRED`,
  `SYNC_UPDATES_AVAILABLE`.
- **iOS** (Google sign-in redirect mode, Plaid `redirect_uri` + OAuth return
  page) and native Android/iOS apps.
- Manual include/exclude **overrides** (the `Transaction` model already carries
  the flags to support it).
- **Refund/inflow netting.**
- **Trends / history** UI (data is already retained).
- **DynamoDB** repository implementation if scale/query needs grow.
- Additional **IdPs** (Apple, Facebook) as additive OIDC verifiers.
- **Recurring-stream tuning** — e.g. only exclude monthly/annual streams, so
  habits Plaid flags as recurring still count.
- Weekly **budget target** to compare the number against.

## Appendix A. Exclusion table (Plaid PFC v2)

The contents of `PFC_RULES`, applied by `classify` (§9): an `amount <= 0`
row is `inflow` before any lookup; a detailed entry wins over its primary's
entry; a key with no entry (and a null PFC) falls through to the recurring
check, then `none`. Keys are full PFC v2 values.

| Key                                     | Level    | Verdict      | Notes                                                                                                                                                                                                                                                      |
| --------------------------------------- | -------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TRANSFER_IN`                           | primary  | `transfer`   | all detailed values                                                                                                                                                                                                                                        |
| `TRANSFER_OUT`                          | primary  | `transfer`   | all detailed values except the two below                                                                                                                                                                                                                   |
| `TRANSFER_OUT_TRANSFER_OUT_FROM_APPS`   | detailed | `COUNT`      | Plaid: "money transferred out of the account into another application"                                                                                                                                                                                     |
| `TRANSFER_OUT_WITHDRAWAL`               | detailed | `COUNT`      | Plaid: "withdrawals from a bank account" (e.g. ATM cash)                                                                                                                                                                                                   |
| `OTHER`                                 | primary  | `transfer`   | constant `PFC_OTHER_IS_MISC_TRANSFER`: Plaid maps its only detailed value, `OTHER_OTHER`, to v1's `TRANSFER_IN_OTHER_TRANSFER_IN` / `TRANSFER_OUT_OTHER_TRANSFER_OUT`; those v2 detailed values still exist and are already covered by the primaries above |
| `LOAN_PAYMENTS_CREDIT_CARD_PAYMENT`     | detailed | `cc_payment` |                                                                                                                                                                                                                                                            |
| `LOAN_PAYMENTS`                         | primary  | `bill`       | `LOAN_PAYMENTS_CAR_PAYMENT`, `_MORTGAGE_PAYMENT`, `_PERSONAL_LOAN_PAYMENT`, `_STUDENT_LOAN_PAYMENT`, `_CASH_ADVANCES`, `_EWA`, `_OTHER_PAYMENT`                                                                                                            |
| `LOAN_PAYMENTS_BNPL`                    | detailed | `COUNT`      | installments usually form a recurring stream, so `classify` normally returns `recurring`                                                                                                                                                                   |
| `RENT_AND_UTILITIES`                    | primary  | `bill`       | all detailed values                                                                                                                                                                                                                                        |
| `GENERAL_SERVICES_INSURANCE`            | detailed | `bill`       | Plaid: "insurance for auto, home, and healthcare"                                                                                                                                                                                                          |
| `GENERAL_SERVICES_CHILDCARE`            | detailed | `bill`       | Plaid: "babysitters and daycare"                                                                                                                                                                                                                           |
| `GENERAL_SERVICES_EDUCATION`            | detailed | `bill`       | Plaid: "elementary, high school, professional schools, and college tuition"                                                                                                                                                                                |
| `BANK_FEES`                             | primary  | `bank_fee`   | all detailed values                                                                                                                                                                                                                                        |
| `MEDICAL`                               | primary  | `medical`    | all detailed values (includes pharmacies and veterinary care)                                                                                                                                                                                              |
| `GOVERNMENT_AND_NON_PROFIT_TAX_PAYMENT` | detailed | `tax`        | donations still count                                                                                                                                                                                                                                      |

A transaction with a null `pfc_primary` is charted under the synthetic key
`UNCATEGORIZED` (constant `NO_PFC_CATEGORY`), never `OTHER`, which is Plaid's
transfer bucket above.

Source: <https://plaid.com/documents/pfc-taxonomy-all.csv> (pinned copy in the
repo, §12 Testing).
