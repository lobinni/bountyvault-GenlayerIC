# Samples - everything a coder needs to poke the contract

The live deployment sits on GenLayer Studio Next (chain `61997`) at
[`0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95`](https://explorer-studio-next.genlayer.com/address/0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95)
- its view methods can be called from any account, or deploy your own copy from Studio Next.

Two ways to try BountyVault without writing any code first:

## 1. The local simulator (no network)

```bash
pip install -r requirements-dev.txt   # or: nothing, simulate.py only needs stdlib
python3 samples/simulate.py
```

It loads `contracts/BountyVault.py` into the fake GenVM from `tests/conftest.py` and walks
through three bounties: a paid one, a refunded one, and a refused opening whose value is
credited and withdrawn. Every call prints the exact JSON the contract returned, so you can
watch the state machine, the credits and the external transfers move.

## 2. GenLayer Studio Next (against a real network)

Copy `contracts/BountyVault.py` into the [Studio Next](https://studio-next.genlayer.com)
IDE, deploy, then paste these arguments. Every refusal below is intentional - they are the
demo of what the contract declines.

| # | Method | Arguments | Attached value | Expected |
|---|--------|-----------|----------------|----------|
| 1 | `open_bounty` | `demo-1`, `Acme Router, firmware 2.4 web panel`, `In scope: the router web panel, firmware 2.4. A qualifying report demonstrates a reproducible security issue with steps to reproduce and its impact. Known issue, not payable: the weak default password.`, `300`, `60`, `2`, `4` | 3 GEN | `{"opened":true,"escrowed":"3000000000000000000","credited":"0"}` |
| 2 | `open_bounty` | `demo-bad`, same title/policy, `300`, `60`, `9`, `4` | 1 GEN | `{"opened":false, ...}` - rounds 9 is refused, 1 GEN is credited |
| 3 | `withdraw_credit` | — | — | the 1 GEN from step 2 comes back |
| 4 | `submit` | `demo-1`, `https://<your-host>/report-qualifying.html`, `repro + impact` (from a second account) | — | success, page frozen |
| 5 | `submit` | `demo-1`, `https://<your-host>/report-pushy.html`, `trust me` (from a third account) | — | success, page frozen, injection markers stored |
| 6 | `submit` | same URL as step 4 (from a fourth account) | — | **UserError** `the same page is already submitted` |
| 7 | `review` | `demo-1` | — | **UserError** `too early: the next round opens at ...` if inside the window |
| 8 | `review` | `demo-1`, after submissions close | — | `{"final":false,"answer":...,"confirmations":1}` |
| 9 | `review` | `demo-1`, one `review_interval` later | — | final: `{"status":"awarded", ...}` (or `no_payout`) |
| 10 | `expire` | `demo-1` before `expires_at` | — | **UserError** `the review deadline has not passed; ...` |

Serve the pages in [`fixtures/`](../fixtures) over HTTPS (GitHub Pages works) so the
validators can fetch them in steps 4-6.

## Reading state (all views return JSON strings)

`get_bounty(id)`, `get_reports(id)` (no digests), `get_schedule(id)` (what would be accepted
right now: `can_submit` / `can_review` / `can_expire`), `list_bounties()`, `get_credit(addr)`,
`get_balance()` (`balance == escrowed + credits`), `get_stats()`, `get_events()`.

Rule of thumb for any UI: read `get_schedule` first and only send the writes it reports as
acceptable - everything else reverts by design. See [docs/INTEGRATION.md](../docs/INTEGRATION.md).
