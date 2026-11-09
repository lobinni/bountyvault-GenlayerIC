# BountyVault - deploy record

| | |
|---|---|
| **Network** | GenLayer Studio Next - chain `61997` |
| **RPC** | `https://studio-next.genlayer.com/api` |
| **Contract** | [`0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95`](https://explorer-studio-next.genlayer.com/address/0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95) |
| **Source** | [`contracts/BountyVault.py`](contracts/BountyVault.py) - `# v0.3.0` stamp, runner `py-genlayer:babwp9t37jw9g4j2bccgn14g6x7x9s1f7dsmh7emvz735pz4zxa0` (the runner the GenVM v0.3.0-rc10 bundle pins on this chain) |
| **Source sha256 (LF)** | `2449c3c2b89e6e16e24c09d5de04e71b30eed8ef1afadb8dac38ceff339e7a3e` |
| **On-chain sha256 (raw)** | `9ca3762bfb1474ac3c04a3734f47216d76286e8a333a51986d2ccb31d8c66277` |
| **Schema dry-run** | `python3 scripts/check_schema.py` → OK (all 13 methods), verified before deploy |

The deploy went through the Studio editor, which stored the source with CRLF line endings.
Line endings are a property of the paste channel, not of the code:
`sha256(adjust to LF, on-chain) == sha256(repository file)`, and
`scripts/verify_deployment.py` proves it on every CI run - both raw hashes are printed next
to the normalized ones. The deployer address has no role in the contract; there is no role
to have.

## Verify the source yourself

```bash
curl -s -X POST https://studio-next.genlayer.com/api -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"gen_getContractCode","params":["0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95"]}' \
  | python3 -c "import sys,json,base64,hashlib; d=base64.b64decode(json.load(sys.stdin)['result']); print(hashlib.sha256(d.replace(b'\r\n',b'\n')).hexdigest())"
shasum -a 256 contracts/BountyVault.py
# both print 2449c3c2b89e6e16e24c09d5de04e71b30eed8ef1afadb8dac38ceff339e7a3e
```

or simply `python3 scripts/verify_deployment.py` (address and RPC are baked in; both can be
overridden with `CONTRACT_ADDRESS` / `GENLAYER_RPC`).

## Lint

`sh scripts/lint.sh` - `genvm-lint lint` on the deployed file, then `check` and `typecheck`
on a copy whose header and imports are switched to the public runner (the bundle-pinned
runner is not in any public GenVM release, so the linter cannot download its SDK; the
contract body is byte-identical). CI runs it on every push.

## The demo run

Record every transaction of the demo here as it happens - refused ones included, they are
the point. The call sheet to follow is [samples/README.md](samples/README.md); serve the
pages in [fixtures/](fixtures) over HTTPS first.

| Role | Address |
|---|---|
| sponsor | `0x…` |
| hunter A | `0x…` |
| hunter B | `0x…` |
| stranger (runs review rounds) | `0x…` |

| # | Call | Sender | Result | What happened | Tx |
|---|------|--------|--------|---------------|----|
| 1 | `open_bounty(…)` value … GEN | sponsor | SUCCESS | … | `0x…` |
| 2 | `open_bounty(…)` rounds 9 | anyone | SUCCESS | refused in return value, amount credited | `0x…` |
| 3 | `withdraw_credit()` | anyone | SUCCESS | credit returned | `0x…` |
| 4 | `submit(…)` | hunter A | SUCCESS | report page frozen | `0x…` |
| 5 | `submit(…)` duplicate page | hunter B | **ERROR** | UserError `the same page is already submitted` | `0x…` |
| 6 | `review(…)` inside the window | stranger | **ERROR** | UserError `too early: the next round opens at …` | `0x…` |
| 7 | `review(…)` | stranger | SUCCESS | round 1: proposal | `0x…` |
| 8 | `review(…)` one interval later | stranger | SUCCESS | agreeing round: `awarded` | `0x…` |
| 9 | `expire(…)` after settlement | stranger | **ERROR** | UserError `the bounty is settled` | `0x…` |

End state: … · contract balance … · `get_balance()` reports `balance == escrowed + credits`.

Previous deployments: none - this is the deployment of record.
