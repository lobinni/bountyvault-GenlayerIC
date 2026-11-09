# Testing BountyVault

Everything runs locally and deterministically - no chain, no network, no sleeps. The suite
drives the deployed source through a fake GenVM so every time rule, every refusal and every
wei is observable.

## Run it

```bash
pip install -r requirements-dev.txt
python3 -m pytest -q            # 81 tests
python3 -m pytest -q -k deadline   # one family at a time
python3 samples/simulate.py     # the same protocol, narrated line by line
sh scripts/lint.sh              # official GenVM linter (pip install genvm-linter)
```

## How the harness works

`tests/conftest.py` installs a fake `genlayer` module before the contract source is exec'd,
so **the deployed file runs unmodified** - the same bytes CI hashes against the chain.

| Knob | Meaning |
| --- | --- |
| `gl.clock` | the transaction datetime in unix seconds; `advance(gl, n)` moves it. On chain GenVM pins the clock to the transaction, so time rules are enforceable, and tests never sleep. |
| `gl.page` | what `nondet.web.render` returns (a string, or an `Exception` to simulate a fetch failure) |
| `gl.llm_reply` | the validators' model answer (string/dict, or an `Exception` for a model failure) |
| `gl.comparative_fails` | when `True`, `eq_principle.prompt_comparative` raises - a consensus failure |
| `gl.prompts` | every prompt sent; tests assert fencing, flags and budget against it |
| `gl.balance` | wei the contract holds; `pay(gl, method, value, *args)` attaches value |
| `gl.transfers` | every external wallet transfer emitted `(address, wei)` |

Two network truths are reproduced exactly:

- **Value survives a revert.** `pay()` adds the attached value to the contract balance even
  when the call raises - which is why `open_bounty` must never raise once value is attached.
- **Time is transaction time.** `datetime.now()` inside the contract reads `gl.clock`, like
  the pinned transaction datetime on chain.

## What each family proves

| Section in `tests/test_bountyvault.py` | The risk it kills |
| --- | --- |
| the happy path | agreeing rounds pay exactly once; `none` and "no reports" refund without asking a model; a different answer restarts the count |
| the sponsor has no power | source scans: no `owner`/`admin`/setters/cancel; `review` takes an id and nothing else; the sponsor cannot submit |
| reports | one per address, closing time in elapsed seconds, the cap, unreadable pages, frozen pages proofs, bad URLs, duplicate hashes |
| it cannot be hurried | no round before close or inside the interval; midnight boundary; hammering cannot finalize early |
| nothing malformed becomes a result | 12 malformed model answers, model error and consensus failure revert and leave no trace; only `gl.vm.UserError` is raised |
| the model cannot be steered | fences balance, injection is flagged and stored, scope/tie-break rules are in the prompt, long pages stay within budget |
| expiry | unresolved bounties refund after the deadline; settled ones cannot be paid twice |
| money | single payable method, single transfer site, refused openings credit everything, books are saved before the transfer, bounties never share money, 250-step random run keeps `balance == escrowed + credits` |
| the deadline | second-by-second exclusivity of `review` vs `expire`, racing calls reach exactly one outcome |
| the views tell the truth | opening order, event log, stats by status, credit defaults, `unknown bounty_id` everywhere |
| `test_contract_source.py` | the header stamp, the chain-pinned runner and the SDK style are exactly what chain 61997 executes; the source stays ASCII-only |

## Writing a new test

```python
def test_my_scenario(env):
    mod, gl, c = env                 # module, fake genlayer, fresh contract
    open_b(gl, c, rounds="2")        # helpers: open_b, submit, full, review
    submit(gl, c, ALICE)             # steers gl.page and the sender for you
    advance(gl, HOUR)
    gl.llm_reply = '{"payout": 0}'   # what validators' model will answer
    out = review(gl, c)              # advances the clock, then calls review()
    assert out["confirmations"] == 1
    assert books(gl, c)              # balance == escrowed + credits == gl.balance
```

Keep the invariant: call `books(gl, c)` after any money-moving scenario, and assert on
`gl.transfers` for the external payouts.

## Against the live deployment

The deployment of record sits on GenLayer Studio Next (chain 61997) at
[`0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95`](https://explorer-studio-next.genlayer.com/address/0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95).
Before touching it with a write, dry-run the interface for free:
`python3 scripts/check_schema.py` - this is the exact call the deploy dialog makes, so a
green result means no "could not load contract schema" surprise.

Host the three pages in `fixtures/` over HTTPS, then follow the call sheet in
[samples/README.md](../samples/README.md) - its refused calls are part of the demo, and
`DEPLOY_RECORD.md` has the table to log them in. Reads are free: any view method above works
against the live contract from a fresh account.
