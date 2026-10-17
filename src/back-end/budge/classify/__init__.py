"""Exclusion classifier: decides whether a transaction counts toward discretionary spend (spec §5, §9, Appendix A).

The verdict comes from the transaction's sign, its Plaid personal finance category (PFC v2), and whether its stream
is a recurring outflow.

Boundary: pure logic with no I/O. It takes plain values and returns a verdict, so it is table-tested against every
PFC v2 detailed category.
"""
