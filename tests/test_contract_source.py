"""Source invariants: the file must carry exactly what chain 61997 executes.

Chain 61997 (Studio Next) pins the runner of its current GenVM bundle and refuses anything
else at schema time. These tests fail the moment the header, the runner or the SDK style
drifts from what the network accepts - long before a deploy attempt does.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "contracts" / "BountyVault.py").read_text(encoding="utf-8")

# The runner pinned by the GenVM v0.3.0-rc10 bundle on Studio Next (chain 61997).
# Bundles churn with releases; if the node answers `runner absent`, look up the current id
# in docs/DEPLOYMENT.md and update this constant together with the header below.
CHAIN_RUNNER = "py-genlayer:babwp9t37jw9g4j2bccgn14g6x7x9s1f7dsmh7emvz735pz4zxa0"


def test_the_header_pins_the_chain_runner():
    lines = SOURCE.splitlines()
    assert lines[0] == "# v0.3.0"
    assert lines[1] == f'# {{ "Depends": "{CHAIN_RUNNER}" }}'
    assert SOURCE.count('"Depends"') == 1


def test_the_sdk_style_is_what_the_chain_executes():
    assert "import genlayer as gl\n" in SOURCE
    assert "from genlayer.types import Address\n" in SOURCE
    assert "class BountyVault(gl.contract.Contract):" in SOURCE
    assert "from genlayer import *" not in SOURCE


def test_the_source_is_ascii_only():
    """The node's schema tooling encodes contract code as ASCII; keep the source pure ASCII."""
    data = (ROOT / "contracts" / "BountyVault.py").read_bytes()
    assert data == data.decode("ascii").encode()
