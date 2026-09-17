"""The same AI-generated cases, as a parametrised pytest suite.

    pytest tests/test_generated.py -v

This is the CI-shaped version of tests/runner.py. Nothing about the cases
changes - only the reporting. That is the point worth making on stage: once the
model's output is structured data, it is just a test suite.
"""

import json
from pathlib import Path

import httpx
import pytest

from tests.runner import BASE, evaluate, send

CASES = json.loads(
    (Path(__file__).resolve().parent.parent / "ai" / "generated_cases.json").read_text()
)["cases"]


@pytest.fixture(scope="module")
def client():
    with httpx.Client(timeout=15.0) as c:
        c.post(f"{BASE}/_reset")
        yield c


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_ai_case(client, case):
    for _ in range(case.get("repeat", 1)):
        resp = send(client, case)
    verdict, detail = evaluate(case, resp)
    assert verdict == "PASS", (
        f"{case['id']} {case['objective']}\n"
        f"  {detail}\n"
        f"  suspected: {case['potential_vulnerability']}\n"
        f"  body: {resp.text[:200]}"
    )
