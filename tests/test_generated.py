"""The same AI-generated cases, as a parametrised pytest suite.

    pytest tests/test_generated.py -v
    CASES=ai/live_cases.json pytest tests/ -v

This is the CI-shaped version of tests/runner.py. Nothing about the cases
changes - only the reporting. That is the point worth making on stage: once the
model's output is structured data, it is just a test suite.

Each test resets the database itself, so `-k`, `-x` and reordering do not
change any verdict. The suite is EXPECTED to fail against this API.
"""

import os

import httpx
import pytest

from tests.runner import DEFAULT_CASES, evaluate, execute_case, load_cases

CASES = load_cases(os.environ.get("CASES", DEFAULT_CASES))


@pytest.fixture(scope="module")
def client():
    with httpx.Client(timeout=15.0) as c:
        yield c


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_ai_case(client, case):
    resp = execute_case(client, case)
    verdict, detail = evaluate(case, resp)
    assert verdict == "PASS", (
        f"{case['id']} {case['objective']}\n"
        f"  {detail}\n"
        f"  suspected: {case['potential_vulnerability']}\n"
        f"  body: {resp.text[:200]}"
    )
