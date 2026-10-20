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
  1. KMS key for Pulumi secrets and state, with the alias alias/budge-pulumi-secrets and
     automatic key rotation on. It comes first because the state bucket encrypts with it.
  2. S3 state bucket budge-pulumi-state-<account_id>: Block Public Access; default
     encryption SSE-KMS with that key (S3 Bucket Key on); a bucket policy that denies
     requests without TLS (aws:SecureTransport false); versioning on, with a lifecycle rule
     that expires noncurrent versions after 90 days.
  3. GitHub Actions OIDC identity provider (token.actions.githubusercontent.com).
  4. Deploy role, assumable through OIDC only by this repository's workflows on main (or a
     deploy environment), not by pull requests or other branches. It gets read/write on
     the state bucket, kms:Encrypt/Decrypt/GenerateDataKey on the key (state and secrets),
     and permissions for the resources the stack manages.

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
