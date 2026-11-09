#!/usr/bin/env python3
"""Fail the build if the deployed BountyVault stops matching contracts/BountyVault.py.

Deployment of record (checked by default, on every CI run):

  GenLayer Studio Next (chain 61997)     0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95

The studio editor stored the source with CRLF line endings. Line endings are a property of
the paste channel, not of the code, so both sides are normalized to LF before hashing; the
raw hashes are printed as well for full transparency.

One-off check of any deployment (e.g. a redeploy):

  CONTRACT_ADDRESS=0x… [GENLAYER_RPC=https://…] python3 scripts/verify_deployment.py
"""

import base64
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

RPC = os.environ.get("GENLAYER_RPC", "https://studio-next.genlayer.com/api")
ADDRESS = os.environ.get("CONTRACT_ADDRESS", "0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95").strip()
SOURCE = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "BountyVault.py"


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def on_chain_bytes() -> bytes:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "gen_getContractCode", "params": [ADDRESS]}
    ).encode()
    request = urllib.request.Request(
        RPC,
        data=payload,
        headers={"content-type": "application/json", "user-agent": "bountyvault-ci/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if "result" not in body:
        raise SystemExit(f"RPC error: {body.get('error')}")
    return base64.b64decode(body["result"])


def main() -> int:
    local = SOURCE.read_bytes()
    remote = on_chain_bytes()
    print(f"local           {hashlib.sha256(local).hexdigest()}")
    print(f"on-chain        {hashlib.sha256(remote).hexdigest()}")
    local_norm = hashlib.sha256(_lf(local)).hexdigest()
    remote_norm = hashlib.sha256(_lf(remote)).hexdigest()
    print(f"LF-normalized   {local_norm} (local)")
    print(f"LF-normalized   {remote_norm} (on-chain)")
    if local_norm != remote_norm:
        print("MISMATCH: redeploy this exact source before submitting")
        return 1
    print("match:", ADDRESS, "on", RPC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
