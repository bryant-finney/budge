"""Plaid client: the calls onboarding, sync, and teardown make to the Plaid API (spec §4, §7).

Covers Link token creation and public-token exchange for onboarding, `/transactions/sync` and
`/transactions/recurring/get` for data, and `/item/remove` for teardown.

Boundary: Plaid response types stop here; callers receive `budge` models. Access tokens are read from the
`SecretStore` protocol, never from the `Repository`.
"""
