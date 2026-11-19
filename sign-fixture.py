"""Versioned portable receipt fixture used only in the protected Actions pilot."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess


def encoded(value):
    return json.dumps(value, separators=(",", ":")).encode()


fixture = Path("fixture.txt").read_bytes()
if fixture != b"synthetic counted result\n":
    raise SystemExit("fixture gate failed")
head = os.environ["GITHUB_SHA"]
policy_key = sha256(b"check-synthetic-fixture-v1").hexdigest()
manifest = sha256(fixture).hexdigest()
receipt = encoded({
    "schema": 1, "jackstay": "synthetic-ci-pilot", "head": head,
    "key": policy_key, "manifest": manifest,
    "outcome": "passed", "evidence_count": 1,
    "ended": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}) + b"\n"
result = Path("evidence")
result.mkdir()
(result / "receipt.json").write_bytes(receipt)
claim = {
    "schema": 1, "trust_root": "protected-pilot-v1", "issuer": "github-actions",
    "repository": os.environ["GITHUB_REPOSITORY"],
    "workflow": ".github/workflows/protected-receipt-pilot.yml",
    "run": os.environ["GITHUB_RUN_ID"] + "." + os.environ["GITHUB_RUN_ATTEMPT"],
    "head": head, "key": policy_key, "manifest": manifest,
    "receipt_sha256": sha256(receipt).hexdigest(),
}
# Keep the disposable signing key in memory. OpenSSL uses stdin for the key and a
# regular file for Ed25519's one-shot signing input.
claim_file = Path("claim.json")
claim_file.write_bytes(encoded(claim))
signature = subprocess.run(
    ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", "/dev/stdin", "-in", str(claim_file)],
    input=(os.environ["PILOT_SIGNING_KEY"].rstrip() + "\n").encode(),
    check=True, capture_output=True,
).stdout.hex()
(result / "attestation.json").write_bytes(encoded({"claim": claim, "signature": signature}) + b"\n")
