# Deploying BountyVault

## Deployment of record

| | |
|---|---|
| **Network** | GenLayer Studio Next - chain `61997` (`https://studio-next.genlayer.com/api`) |
| **Contract** | [`0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95`](https://explorer-studio-next.genlayer.com/address/0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95) |
| **Record** | [DEPLOY_RECORD.md](../DEPLOY_RECORD.md) |

Full protocol details live in the record; the mechanics of verifying and re-deploying are
below.

## The pinned runner

Contract runners change with GenVM bundles. Chain 61997 currently runs GenVM v0.3.0-rc10
and pins `py-genlayer:babwp9t37jw9g4j2bccgn14g6x7x9s1f7dsmh7emvz735pz4zxa0`; the header of
`contracts/BountyVault.py` declares exactly that (plus the `# v0.3.0` stamp and the
`import genlayer as gl` / `gl.contract.Contract` SDK shape every live contract on this
network carries). Sources built for other runners are refused at schema time:

```
gen_getContractSchemaForCode … {"kind": "VM_ERROR", "message": "invalid_contract runner malformed"}
```

That error means *the chain does not accept this runner*, not that the contract is broken.
If a future bundle moves the pin again (the message becomes `runner absent`), look up the
current runner by reading the first lines of any contract freshly deployed through the
Studio UI (`gen_getContractCode`), update the header of `contracts/BountyVault.py` and
`CHAIN_RUNNER` in `tests/test_contract_source.py`, and re-run the dry run below.

## 1. Validate locally

```bash
pip install -r requirements-dev.txt genvm-linter
python3 -m pytest -q        # 81 tests, all green before anything leaves the machine
sh scripts/lint.sh          # genvm-lint on the deployed file + full SDK check on a copy
```

Note on linting: the bundle-pinned runner is not in any public GenVM release, so
`genvm-lint check`/`typecheck` (which download the runner SDK) run on a temporary copy whose
header and imports are switched to the public runner `1jb45aa8…`. `lint` itself runs on the
deployed file as-is; the contract body is byte-identical either way. The script does the
swap for you.

## 2. Dry-run the schema (the exact call Studio makes)

"Could not load contract schema" in the deploy dialog is `gen_getContractSchemaForCode`
failing on the node. Call it yourself, for free, first:

```bash
python3 scripts/check_schema.py     # contracts/BountyVault.py on Studio Next (61997)
```

On success it prints every public method with its flags (`view` / `payable`); on failure it
prints the node's own VM error. It also refuses non-ASCII sources up front - the schema
tooling encodes contract code as ASCII.

## 3. Deploy

Open [GenLayer Studio Next](https://studio-next.genlayer.com), paste
`contracts/BountyVault.py` into the IDE, deploy with the constructor defaults (there is
nothing to parameterize), and note the contract address.

One practical note: the Studio editor may store the pasted source with CRLF line endings
(that is what happened to the deployment of record). The code is identical - only line
endings differ - so the verification normalizes both sides to LF before hashing. If you
want a raw-byte match instead, deploy from a channel that preserves LF (CLI), and the
script's raw hashes will agree too.

The deployer receives **no** role: the contract has no privileged account, so who deploys
it does not matter.

## 4. Record and verify

1. Keep [DEPLOY_RECORD.md](../DEPLOY_RECORD.md) current: address, network, source sha256,
   and the demo run - every transaction, refused ones included.
2. `scripts/verify_deployment.py` compares on-chain bytes to `contracts/BountyVault.py` and
   fails CI on any drift:

```
local           2449c3c2…339e7a3e
on-chain        9ca3762b…d8c66277   (CRLF as stored by the editor)
LF-normalized   2449c3c2…339e7a3e (local)
LF-normalized   2449c3c2…339e7a3e (on-chain)
match: 0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95 on https://studio-next.genlayer.com/api
```

Verify by hand at any time:

```bash
curl -s -X POST https://studio-next.genlayer.com/api -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"gen_getContractCode","params":["0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95"]}' \
  | python3 -c "import sys,json,base64,hashlib; d=base64.b64decode(json.load(sys.stdin)['result']); print(hashlib.sha256(d.replace(b'\r\n',b'\n')).hexdigest())"
shasum -a 256 contracts/BountyVault.py
# both print 2449c3c2b89e6e16e24c09d5de04e71b30eed8ef1afadb8dac38ceff339e7a3e
```

`CONTRACT_ADDRESS` and `GENLAYER_RPC` env vars override the baked-in record (CI also reads
`CONTRACT_ADDRESS` from repo variables).

## 5. Demo run

Follow the call sheet in [samples/README.md](../samples/README.md): open one bounty that
will be paid, one that will be refused (rounds = 9) and withdrawn, submit the pages from
`fixtures/` over HTTPS, run review rounds, and try `expire` too early - the refusals are
part of the demo. Host the fixture pages where validators can reach them (GitHub Pages is
enough).

## Checklist before submitting

- [ ] `python3 -m pytest -q` - all green
- [ ] `black --check contracts tests samples scripts` and `flake8 …` - clean (CI)
- [ ] `python3 scripts/check_schema.py` - schema loads on Studio Next
- [ ] `sh scripts/lint.sh` - lint / check / typecheck clean
- [ ] deployed the exact committed bytes (`verify_deployment.py` prints `match`)
- [ ] `DEPLOY_RECORD.md` lists every transaction, including the refused ones
