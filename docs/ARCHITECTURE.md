# BountyVault - architecture

Everything below describes `contracts/BountyVault.py` as it stands. The file is deliberately
one module: GenVM deploys one file, and keeping the whole protocol in one file is what lets
CI assert `sha256(on-chain) == sha256(repo)`.

## Layers

```
                        ┌────────────────────────────────────────────┐
  writes (consensus)    │ open_bounty  submit  review  expire        │
                        │ withdraw_credit                            │
                        ├────────────────────────────────────────────┤
  nondeterminism        │ _capture_page  (web render, strict_eq)     │
   (validators run,     │ decide_payout  (exec_prompt,               │
    then compare)       │                  prompt_comparative)       │
                        ├────────────────────────────────────────────┤
  pure functions        │ ids, urls, text, seconds, small ints       │
                        │ sha256, digest windows, fences, flags      │
                        │ literal_index, verdict parsing             │
                        ├────────────────────────────────────────────┤
  storage               │ bounties_json  reports_json  order_json    │
   (one JSON blob       │ credits_json   events_json                 │
    per concern)        │                                            │
                        └────────────────────────────────────────────┘
```

No layer may skip downward: writes never format prompts by hand, consensus helpers never
touch storage, pure helpers never raise anything but `gl.vm.UserError`.

## State machine

`open` → `reviewing` → (`awarded` | `no_payout`), plus `expired` from either live state.
Terminal states are irreversible - `_pay_out` refuses when `paid_out` already covers the
reward, so no path pays twice.

| Transition | Method | Guard |
| --- | --- | --- |
| → open | `open_bounty` | valid args, unique id, value in `(0, 10^24]`; otherwise credited, not raised |
| open → open | `submit` | before `submissions_close_at`, caller ≠ sponsor, one per address, cap, https URL, page captured `ok`, hash unseen |
| open → reviewing | `review` | `next_round_at <= now < deadline`; then an agreed answer exists or it reverts |
| reviewing → reviewing | `review` | same, with the interval measured from the previous accepted round |
| → awarded / no_payout | `review` | `confirmations == rounds_required` |
| → no_payout | `review` | zero reports: refund without asking a model |
| → expired | `expire` | `now >= deadline` |

`deadline = submissions_close_at + (rounds_required + GRACE_ROUNDS) * review_interval`,
computed once from values fixed at opening. `review` refuses at `now >= deadline`; `expire`
refuses before it. The two accept sets are disjoint for every second, which is what makes
racing the deadline pointless.

## The nondeterministic core

### Freezing a page (`submit`)

1. The leader renders the URL (`text`, falling back to `html`) and normalizes whitespace.
2. `content_hash = sha256(normalized)` - identity of the page, used for the duplicate
   refusal and auditable by anyone.
3. `build_digest` - a bounded (1500 chars, ≤3 windows of 400) deterministic view: a short
   page is kept whole; a long one gets the head, then windows around the program's own
   keywords (every occurrence tried, not only the first), then the first uncovered
   stretches, so budget never strands an unread gap next to an existing window.
4. All validators re-run the leader function under `eq_principle.strict_eq`; disagreement
   reverts before anything is stored.
5. A page whose fetch fails or is empty stores nothing: the call reverts with
   `the report page could not be read; nothing was submitted`.

### Agreeing on a payout (`review`)

The prompt is assembled from the frozen digests only. Title, policy, every note and every
excerpt are wrapped in `<<<BEGIN/END_UNTRUSTED_DATA>>>` fences; any fence-like string inside
the data is scrubbed to `[fence-removed]` so the fence count always balances; known
instruction-like markers (`ignore previous`, `this report qualifies`, `"payout":`, …) are
detected, injected into the prompt as a warning, and stored on the bounty (max 6).

The leader answers strict JSON: `{"payout": N}` or `{"payout": null}`. Only a real JSON
integer indexing an existing report survives `literal_index`; `true`, `"0"`, `0.0`, `7`,
names, arrays, missing keys and non-JSON all become an `invalid` verdict, and `invalid`
reverts the whole round. Validators compare with `eq_principle.prompt_comparative` on the
`verdict` field (`none` / `report:N`, identical bytes). A consensus failure raises and the
round leaves no trace - not even the interval is consumed.

The policy rules baked into the prompt: judge only against the acceptance policy; an issue
the policy marks out of scope or already known cannot be paid; a report missing required
evidence cannot be paid; severity a report claims for itself is not evidence; when several
reports qualify, the first submitted (lowest index) is paid - which makes the duplicate-hash
refusal at `submit` time a fairness rule, not just hygiene.

### Rounds

A round that agrees with the standing proposal adds one confirmation; a different agreed
answer replaces the proposal and restarts the count at 1. `rounds_required` consecutive
agreements settle the bounty. Rounds are separated by elapsed time (`next_round_at`), so
spamming the method cannot hurry settlement, and a midnight boundary changes nothing.

## Money

- Value attached to a **reverted** call is not returned by the network. Hence
  `open_bounty` never raises when value is attached: every refusal credits the sender and
  reports `{"opened": false}` in the return value. With no value attached it raises.
- Internal messages cannot move GEN to a wallet. Payouts use an external transfer via the
  ghost contract of the recipient; the books (`paid_out`, `status`, `settled_at`) are saved
  **before** the transfer is emitted - reordered lines would break this and the source-scan
  test would fail.
- Invariant at every step of every test, including a 250-step random run:
  `contract balance == sum(reward - paid_out) + sum(credits)`.

## Storage

All state lives in five JSON strings (GenVM stores the values you declare). Strings, not
numbers, for wei amounts - JSON numbers would lose precision. Bounty fields include the full
audit trail: `proposal`, `confirmations`, `rounds`, bounded `history` (last 24 rounds with
caller and outcome), `injection_flags`, `settled_at`. `get_reports` strips digests so the
view stays small; the digests are only ever consumed inside the prompt.

## Bounds

| Constant | Value | Why |
| --- | --- | --- |
| `MAX_ID_LEN` / `MAX_TITLE_LEN` / `MAX_POLICY_LEN` / `MAX_NOTE_LEN` | 64 / 120 / 900 / 200 | storage and prompt hygiene |
| `MAX_URL_LEN` | 2048 | URL abuse |
| `MAX_BOUNTIES` / `MAX_EVENTS` | 200 / 200 | bounded state |
| `MIN_ROUNDS`..`MAX_ROUNDS` | 1..4 | one round is a proposal; more than four buys little |
| `MIN_REPORTS`..`MAX_REPORTS` | 1..8 | the prompt must fit the digest budget |
| `MAX_REWARD_WEI` | 10^24 | caps what one mistake can escrow |
| interval seconds | 60 .. 30 days | enforceable timing |
| `GRACE_ROUNDS` | 3 | slack before an unresolved bounty can expire |
