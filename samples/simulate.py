#!/usr/bin/env python3
"""A full BountyVault lifetime against the fake GenVM - no network, no chain needed.

Runs the contract exactly as the tests do, but narrates every step so you can see the
state machine move:

    bounty-1   two hunters, the model picks report 0, two agreeing rounds -> PAID
    bounty-2   the model answers "none" twice -> refund to the sponsor
    bounty-3   opened with rounds=9 -> refused, credited, withdrawn

Usage:
    python3 samples/simulate.py

The fake harness steers "the network": gl.page is what the web fetch returns and
gl.llm_reply is what the validators' model answers. On a real network both come from
the validators; the contract code is byte-identical either way.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from conftest import PAGE_1, PAGE_3, advance, load_contract, pay, reset  # noqa: E401

HOUR = 3600
GEN = 10**18
SPONSOR = "0x1111111111111111111111111111111111111111"
ALICE = "0x2222222222222222222222222222222222222222"
CAROL = "0x4444444444444444444444444444444444444444"
ANYONE = "0x5555555555555555555555555555555555555555"

POLICY = (
    "In scope: the router web panel, firmware 2.4. A qualifying report demonstrates a "
    "reproducible security issue with steps to reproduce and its impact. Known issue, "
    "not payable: the weak default password."
)


def show(label, value):
    print(f"\n== {label}\n{json.dumps(value, indent=2, sort_keys=True)}")


def books(gl, c):
    b = json.loads(c.get_balance())
    b["matches_chain_balance"] = int(b["balance"]) == gl.balance
    show("books: balance == escrowed + credits", b)


def main() -> None:
    mod = load_contract(ROOT)
    gl = sys.modules["genlayer"]
    reset(gl)
    c = mod.BountyVault()

    gl.message.sender_address = SPONSOR
    show(
        "bounty-1 opened, 5 GEN escrowed",
        json.loads(
            pay(
                gl,
                c.open_bounty,
                5 * GEN,
                "bounty-1",
                "Acme Router, firmware 2.4 web panel",
                POLICY,
                str(HOUR),
                str(HOUR),
                "2",
                "4",
            )
        ),
    )

    gl.page = PAGE_1
    gl.message.sender_address = ALICE
    c.submit("bounty-1", "https://reports.example/alice", "repro + impact for the panel XSS")
    gl.page = PAGE_3
    gl.message.sender_address = CAROL
    c.submit("bounty-1", "https://reports.example/carol", "xss, no repro")
    show("reports after submit (digests hidden by the view)", json.loads(c.get_reports("bounty-1")))

    advance(gl, HOUR)
    gl.llm_reply = '{"payout": 0}'
    gl.message.sender_address = ANYONE
    show("review round 1: proposal", json.loads(c.review("bounty-1")))
    advance(gl, HOUR)
    show("review round 2: agrees -> final, the hunter is paid", json.loads(c.review("bounty-1")))
    show("external transfers the contract emitted", [list(t) for t in gl.transfers])
    books(gl, c)

    gl.message.sender_address = SPONSOR
    pay(
        gl,
        c.open_bounty,
        2 * GEN,
        "bounty-2",
        "Acme Router, firmware 2.4 web panel",
        POLICY,
        str(HOUR),
        str(HOUR),
        "1",
        "4",
    )
    gl.page = PAGE_3
    gl.message.sender_address = CAROL
    c.submit("bounty-2", "https://reports.example/carol-2", "same incomplete style")
    advance(gl, HOUR)
    gl.llm_reply = '{"payout": null}'
    gl.message.sender_address = ANYONE
    show("bounty-2: validators answer none -> refund", json.loads(c.review("bounty-2")))
    books(gl, c)

    gl.message.sender_address = SPONSOR
    refused = json.loads(
        pay(
            gl,
            c.open_bounty,
            1 * GEN,
            "bounty-3",
            "Acme Router, firmware 2.4 web panel",
            POLICY,
            str(HOUR),
            str(HOUR),
            "9",
            "4",
        )
    )
    show("bounty-3 with rounds=9: refused, never raised, credited", refused)
    show("withdrawing the credit", c.withdraw_credit())
    books(gl, c)

    show("events the contract logged", json.loads(c.get_events()))
    print("\ndone. Run the real checks with: python3 -m pytest -q")


if __name__ == "__main__":
    main()
