# Integrating a frontend (the console is a separate project)

This repository is the submission; a UI is deliberately **not** part of it. Everything a
console needs is specified here so the two projects can evolve separately.

**Deployment of record** (reads are free from any account): GenLayer Studio Next, chain
`61997`, RPC `https://studio-next.genlayer.com/api`, contract
[`0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95`](https://explorer-studio-next.genlayer.com/address/0xFBFd9F825518C36D9c5b55Ee1b430fa5f44bbf95).

## The one rule

**Read `get_schedule(bounty_id)` before sending any write.** It answers what would be
accepted right now; anything it reports as not acceptable reverts, still costs a
transaction, and achieves nothing.

```json
{
  "bounty_id": "demo-1", "status": "reviewing", "now": 1767229200, "reports": 2,
  "can_submit": false, "can_review": true, "can_expire": false,
  "next_round_at": 1767229200, "expires_at": 1767247200,
  "confirmations": 1, "rounds_required": 2
}
```

`can_review` and `can_expire` are mutually exclusive for every second by construction.

## Writes

All writes revert with `gl.vm.UserError` and a human-readable message on refusal, except
`open_bounty` with value attached, which returns a refusal JSON instead (see below).

| Method | Value | Who | Happy return |
| --- | --- | --- | --- |
| `open_bounty(id, title, policy, submissions_close_in, review_interval, rounds_required, max_reports)` | reward in wei | sponsor | `{"opened":true,"escrowed":"...","credited":"0"}` |
| `submit(id, report_url, note)` | — | anyone but the sponsor | `null` (raises on refusal) |
| `review(id)` | — | anyone | round: `{"final":false,"answer":N,"confirmations":C,"rounds_required":R}` · final: `{"status":"awarded"|"no_payout","paid_to":"0x…","amount":"…"}` |
| `expire(id)` | — | anyone | `{"status":"expired","paid_to":"0x…","amount":"…"}` |
| `withdraw_credit()` | — | anyone with credit | `"<wei>"` |

`open_bounty` with value attached never raises: on refusal it returns
`{"opened":false,"credited":"<wei>","reason":"…"}`. Show the reason, then let the user call
`withdraw_credit()` to get the amount back.

### Errors a UI should render verbatim

`bounty_id …`, `title/policy …`, `… must be between 60 and 2592000 seconds`,
`open_bounty needs the reward as value`, `unknown bounty_id`, `the bounty is not open`,
`submissions are closed`, `the sponsor cannot submit`, `one report per address`,
`the bounty is full`, `report_url must be https:// …`, `the report page could not be read
…`, `the same page is already submitted`, `the bounty is settled`, `the review deadline has
passed at …; only expire is accepted`, `too early: the next round opens at …`,
`the review deadline has not passed; expiry opens at …`, `no credit for this address`.

## Reads (all return JSON-encoded strings; parse once)

| View | Shape |
| --- | --- |
| `get_bounty(id)` | full bounty incl. `status`, `reward`, `paid_out`, `confirmations`, `proposal`, bounded `history`, `injection_flags` |
| `get_reports(id)` | array of `{index, hunter, url, note, content_hash, total_chars, submitted_at}` - digests are not exposed |
| `get_schedule(id)` | see above |
| `list_bounties()` | `["id", …]` in opening order |
| `get_credit(addr)` | `"<wei>"` |
| `get_balance()` | `{"balance","escrowed","credits"}` with `balance = escrowed + credits` |
| `get_stats()` | `{"bounties":N,"by_status":{…},"settled":"<wei>"}` |
| `get_events()` | bounded log: `BountyOpened`, `Submitted`, `Round`, `Awarded`, `NoPayout`, `NoReports`, `Expired` with payloads |

Statuses: `open` → `reviewing` → `awarded` | `no_payout`, or `expired`.

## Minimal client pseudocode

```ts
// genlayer-js style; the exact SDK belongs to the console repo, not here.
const s = parse(await vault.read.get_schedule(id));
if (s.can_review)      await vault.write.review(id);            // any wallet can
else if (s.can_expire) await vault.write.expire(id);
else                   show(next(s.next_round_at ?? s.expires_at));
```

For deeper reads, render `history`, surface `injection_flags` as a "this report tries to
instruct the reviewer" badge, and link `content_hash` to the frozen page so visitors can
verify a report was not edited after submission.

## What a UI must never offer

Buttons the contract will refuse anyway: sponsor `submit`, a second `submit` from the same
address, `review` inside the interval, `expire` before `expires_at`, and any "edit rules"
action - there is no setter to call.
