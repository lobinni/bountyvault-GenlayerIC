# BountyVault - deploy record (template)

Fill every field after deploying; keep refused transactions in the table - they are part of
the record.

| | |
|---|---|
| **Network** | GenLayer Studio Next - chain `61997` |
| **Contract** | `0x…` |
| **Deploy tx** | `0x…`, from `0x…`, which has no role in the contract |
| **Source** | `contracts/BountyVault.py` - runner `py-genlayer:babwp9t37jw9g4j2bccgn14g6x7x9s1f7dsmh7emvz735pz4zxa0` |
| **Source sha256** | `…` |

## Verify the source yourself

```bash
curl -s -X POST https://studio-next.genlayer.com/api -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"gen_getContractCode","params":["<ADDRESS>"]}' \
  | python3 -c "import sys,json,base64,hashlib; print(hashlib.sha256(base64.b64decode(json.load(sys.stdin)['result'])).hexdigest())"
shasum -a 256 contracts/BountyVault.py
# both print the same hash
```

## Lint

`sh scripts/lint.sh` - `genvm-lint lint`, `check`, `typecheck` on the deployed bytes: passed,
in CI.

## The run

| Role | Address |
|---|---|
| sponsor | `0x…` |
| hunter A | `0x…` |
| hunter B | `0x…` |
| stranger (runs every round) | `0x…` |

| # | Call | Sender | Result | What happened | Tx |
|---|------|--------|--------|---------------|----|
| 1 | `open_bounty(…)` value … GEN | sponsor | SUCCESS | … | `0x…` |
| 2 | `open_bounty(…)` rounds 9 | anyone | SUCCESS | refused in the return value, amount credited | `0x…` |
| 3 | `withdraw_credit()` | anyone | SUCCESS | credit returned | `0x…` |
| 4 | `submit(…)` | hunter A | SUCCESS | page frozen | `0x…` |
| 5 | `submit(…)` duplicate page | hunter B | **ERROR** | UserError `the same page is already submitted` | `0x…` |
| 6 | `review(…)` too early | stranger | **ERROR** | UserError `too early: the next round opens at …` | `0x…` |
| 7 | `review(…)` | stranger | SUCCESS | round 1 proposed | `0x…` |
| 8 | `review(…)` one interval later | stranger | SUCCESS | agreeing round, awarded | `0x…` |
| 9 | `expire(…)` after settlement | stranger | **ERROR** | UserError `the bounty is settled` | `0x…` |

End state: …, contract balance …, `get_balance()` reports `balance == escrowed + credits`.
