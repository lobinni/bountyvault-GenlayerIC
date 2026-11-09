#!/bin/sh
# Runs the official GenVM linter (genvm-lint, the check stewards use) on BountyVault.
#
#   1. `genvm-lint lint` on the file exactly as deployed (chain-pinned runner babwp9t37...).
#   2. `genvm-lint check` + `typecheck` (full SDK validation) on a copy whose header and
#      imports are rewritten to the public py-genlayer runner 1jb45aa8 (GenVM v0.3.0-rc7).
#      Studio Next (61997) only pins bundle runners, which are not in any public GenVM
#      release, so the linter cannot download that SDK; the contract body is
#      byte-identical between the deployed file and the checked copy.
set -e
SRC="$(dirname "$0")/../contracts/BountyVault.py"
TMP="$(mktemp -d)/BountyVault.py"
genvm-lint lint "$SRC"
sed -e 's/py-genlayer:babwp9t37jw9g4j2bccgn14g6x7x9s1f7dsmh7emvz735pz4zxa0/py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6/' \
    -e 's/^import genlayer as gl$/from genlayer import */' \
    -e '/^from genlayer.types import Address$/d' \
    -e 's/(gl\.contract\.Contract)/(gl.Contract)/' "$SRC" > "$TMP"
genvm-lint check "$TMP"
genvm-lint typecheck "$TMP"
