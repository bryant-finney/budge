#!/usr/bin/env bash
# One-time, idempotent AWS bootstrap for budge's Pulumi state (spec §12).
#
# STUB (milestone 1): prints the plan and makes no AWS calls. The real implementation lands in
# milestone 4.
set -euo pipefail

usage() {
	cat <<'EOF'
Usage: src/infrastructure/bootstrap.sh [--help]

One-time, idempotent bootstrap of the AWS resources that the budge Pulumi stack cannot manage
itself, because they hold or protect its own state. Run it with the deploy account's
credentials (AWS_PROFILE from .env) before `pulumi stack init prod`.

Planned steps (region us-east-1; each step is skipped if it is already in place):
  1. S3 state bucket budge-pulumi-state-<account_id>: versioning on, Block Public Access,
     default server-side encryption.
  2. KMS key for Pulumi secrets, with the alias alias/budge-pulumi-secrets.
  3. GitHub Actions OIDC identity provider (token.actions.githubusercontent.com).
  4. Deploy role assumable by this repository's workflows through OIDC, with access to the
     state bucket and the secrets KMS key.

Afterwards:
  PULUMI_BACKEND_URL=s3://budge-pulumi-state-<account_id>?region=us-east-1
  pulumi stack init prod --secrets-provider "awskms://alias/budge-pulumi-secrets?region=us-east-1"

Status: not implemented (milestone 4). This stub makes no AWS calls.

Options:
  -h, --help  Show this help and exit.
EOF
}

case "${1-}" in
-h | --help)
	usage
	;;
*)
	echo "bootstrap.sh: not implemented (milestone 4); see --help for the planned steps" >&2
	exit 2
	;;
esac
