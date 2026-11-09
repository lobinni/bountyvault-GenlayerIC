# BountyVault Core

**A bug bounty the sponsor cannot keep at all, downplay, delay, or hand to a friend.**

This repository holds the Intelligent Contract, its tests, its lint script, its samples and
its docs - and nothing else. It is the submission. The console that talks to it is a separate
project by design: everything a UI needs is specified in [docs/INTEGRATION.md](docs/INTEGRATION.md),
so the contract can be submitted alone.

## Live

| | |
|---|---|
| **Network** | GenLayer Studio Next - chain `61997` (`https://studio-next.genlayer.com/api`) |
| **Contract** | [`0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95`](https://explorer-studio-next.genlayer.com/address/0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95) |
| **Deploy record** | [DEPLOY_RECORD.md](DEPLOY_RECORD.md) - `sha256(on-chain) == sha256(repo)` (LF-normalized), re-checked by CI on every push |

---

## The trust problem

A bounty is only as fair as whoever decides that a report qualifies, and the sponsor usually
both holds the reward and decides. After reading a report they can call it "known" or "out of
scope", keep the reward, and fix the bug quietly anyway. Hunters can also edit the report page
after the deadline.

**BountyVault takes all of that away from the sponsor.** The reward is escrowed in native GEN
when the bounty opens, the acceptance policy is fixed, every report page is frozen at the
moment it is submitted, and the payout is the report that validators agree on in separated
rounds.

```
open_bounty(bounty_id, title, policy, submissions_close_in, review_interval,
            rounds_required, max_reports)                              PAYABLE
     the attached value is the reward. Everything that decides it is fixed here.
     with value attached it never reverts: a bounty it cannot open is refused in the
     return value and the amount is credited to the sender

submit(bounty_id, report_url, note)     one report per address, before submissions close,
                                        never the sponsor. Validators fetch the page and
                                        freeze it (SHA-256 of the whole page + a bounded
                                        digest). Reviewing reads only the frozen copy, and
                                        a page whose frozen hash duplicates an earlier
                                        report never gets in.

review(bounty_id)                       anyone; takes a bounty id and nothing else
     refused before submissions close and before a full review_interval since the last round
     no reports -> the reward goes back to the sponsor, no model asked
     otherwise validators agree on ONE answer: the index of the report that meets the
     acceptance policy, or "none"
       same answer as the standing proposal -> one more confirmation
       a different answer                  -> the count starts again from 1
     rounds_required agreeing rounds -> FINAL: the reward goes to that hunter's wallet
                                        (or back to the sponsor if the answer is none)

expire(bounty_id)                       anyone, after the committed review deadline:
                                        an unresolved bounty returns the reward
withdraw_credit()                       take back what open_bounty refused to escrow
```

### Lifecycle

```
                 open_bounty (reward escrowed)
                    │
                    ▼
        ┌───────   open   ◀────── submit (page frozen) ──────┐
        │           │                                        │
        │           │ submissions_close_at                   │
        │           ▼                                        │
        │       reviewing  ◀─ review round, interval apart ──┘
        │           │            rounds_required agreeing answers
        │           ▼
        │     awarded ──────────────── reward → hunter
        │     no_payout ─ none agreed ─ reward → sponsor
        │     no_payout ─ no reports ─ reward → sponsor
        └──── expired ─── past the review deadline, unresolved ─ reward → sponsor
```

`review` is accepted only **before** the review deadline and `expire` only **at or after** it,
so transaction ordering can never choose between a payout to the hunter and a refund to the
sponsor. The deadline is fixed when the bounty opens:
`submissions_close_at + (rounds_required + 3) × review_interval`.

## Why it fails the way it does

A reward is paid once and cannot be clawed back, so one round is only a proposal and a
pipeline problem never looks like an answer: a malformed model answer, a model error or a
consensus failure **reverts the transaction**.

| Risk | What stops it |
| --- | --- |
| The sponsor calls a real report "not qualifying" | The sponsor does not decide. `review` takes a bounty id and nothing else; the answer is what validators agree on. |
| The sponsor pays a sock puppet | The sponsor cannot submit; one report per address; duplicates of the same page are refused. |
| The policy is rewritten after the reports are in | It is fixed in `open_bounty`; there is no setter, no privileged account. |
| The sponsor keeps the reward | It leaves only to the paid hunter, or back to the sponsor if validators agree no report qualifies, if there were no reports, or past the deadline. |
| A hunter improves the page after the deadline | Pages are frozen when submitted. On chain, the page was never re-read. |
| One lucky or wrong round decides | `rounds_required` agreeing rounds, each a full `review_interval` after the previous one - elapsed time, not a calendar window. A different answer restarts the count. |
| A report tells the reviewer to pay it | Reports, notes, title and policy are fenced as untrusted data, inner fences are neutralized, and instruction-like phrasing is flagged and stored. |
| `"0"`, `true`, `0.0` or a name counted as an answer | `literal_index()` accepts only a JSON integer inside the report list; `null` means none. Anything else reverts. |
| A refused bounty strands its reward | Value attached to a reverting call is not returned on this network, so `open_bounty` never raises once value is attached; the amount is credited. |
| A payout that pays nobody | Wallets are paid by an external transfer, after the books are updated. |
| A bounty nobody reviews | `expire` returns the reward after the committed deadline. |

## Repository layout

```
bounty-vault-core/
├── contracts/BountyVault.py      the Intelligent Contract (the whole submission surface)
├── tests/conftest.py             fake GenVM harness: clock, web, model, balances
├── tests/test_bountyvault.py     78 protocol tests
├── tests/test_contract_source.py header / runner / SDK-style invariants (81 total)
├── fixtures/                     demo report pages for Studio walkthroughs
├── samples/simulate.py           full local lifetime run; samples/README.md call sheets
├── scripts/check_schema.py       free dry-run of the schema call Studio makes
├── scripts/lint.sh               genvm-lint: lint + check + typecheck (public-runner copy)
├── scripts/verify_deployment.py  sha256(on-chain code) == sha256(this repo)
├── docs/                         ARCHITECTURE, DEPLOYMENT, INTEGRATION, TESTING
├── DEPLOY_RECORD.md + template
└── .github/workflows/ci.yml      format, lint, genvm-lint, tests, schema dry-run, parity
```

## Quickstart

```bash
pip install -r requirements-dev.txt
python3 -m pytest -q              # 81 tests
python3 samples/simulate.py       # narrated end-to-end run against the fake GenVM
python3 scripts/check_schema.py   # free schema dry-run on Studio Next (chain 61997)
sh scripts/lint.sh                # needs: pip install genvm-linter
```

## License

[MIT](LICENSE) © 2026 BountyVault contributors
