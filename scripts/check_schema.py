#!/usr/bin/env python3
"""Free compile check: ask Studio Next (chain 61997) to load the contract and return its schema.

The deploy dialog runs `gen_getContractSchemaForCode` (the source, hex-encoded) before it
lets you deploy; "Could not load contract schema" in the UI is exactly this call failing.
Run it yourself first - it costs nothing and returns the node's own error.

Usage:
  python3 scripts/check_schema.py               # contracts/BountyVault.py on Studio Next
  python3 scripts/check_schema.py <file> [--rpc URL]

  CONTRACT_SOURCE / GENLAYER_RPC env vars work too.

Exit 0 = schema loaded. Exit 1 = ASCII violation, RPC error, or a VM error (the node's own
message is printed, e.g. `invalid_contract runner absent` when the GenVM bundle moved and
the pinned runner id changed - see docs/DEPLOYMENT.md for how to look up the current one).
"""

import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
STUDIO_NEXT = "https://studio-next.genlayer.com/api"

HDRS = {
    "content-type": "application/json",
    "origin": "https://studio-next.genlayer.com",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
}


def vm_message(raw: str) -> str:
    for needle in ("invalid_contract runner malformed", "invalid_contract runner absent"):
        if needle in raw:
            return needle
    m = re.search(r'"kind":\s*\\?"VM_ERROR\\?",\s*"message":\s*\\?"([^"\\]+)', raw)
    if m:
        return m.group(1)
    m = re.search(r"'stderr':\s*'([^']{1,400})'", raw)
    if m and m.group(1).strip():
        return "stderr: " + m.group(1).strip()[:300]
    return raw[-400:]


def main(argv) -> int:
    args = [a for a in argv if not a.startswith("--")]
    rpc = os.environ.get("GENLAYER_RPC", STUDIO_NEXT)
    if "--rpc" in argv:
        rpc = argv[argv.index("--rpc") + 1]
    rel = args[0] if args else os.environ.get("CONTRACT_SOURCE", "contracts/BountyVault.py")
    path = (ROOT / rel).resolve()
    data = path.read_bytes()

    bad = [
        (i + 1, ch)
        for i, ch in enumerate(data.decode("utf-8", "replace").splitlines())
        for ch in ch
        if ord(ch) > 127
    ]
    if bad:
        print(
            f"FAIL: {rel} is not ASCII-only ({len(bad)} chars, first at lines "
            f"{sorted({ln for ln, _ in bad})[:8]}). The schema tooling encodes sources as ASCII."
        )
        return 1

    code = "0x" + data.hex()
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "gen_getContractSchemaForCode", "params": [code]}
    ).encode()
    req = urllib.request.Request(rpc, data=body, headers=HDRS)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            out = json.load(resp)
    except Exception as exc:
        print(f"RPC error on {rpc}: {exc}")
        return 1

    if "result" not in out:
        print(f"FAIL: {rel} on {rpc}")
        print("node says:", vm_message(json.dumps(out.get("error", ""))))
        return 1

    schema = out["result"]
    methods = schema.get("methods", {})
    print(f"OK: {rel} loads on {rpc}")
    for name, sig in methods.items():
        flags = []
        if sig.get("readonly"):
            flags.append("view")
        if sig.get("payable"):
            flags.append("payable")
        print(f"  {name}" + ("  " + ",".join(flags) if flags else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
