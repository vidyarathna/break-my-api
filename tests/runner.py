"""Execute AI-generated test cases against the running ConfBadge API.

    AI-generated cases  ->  structured JSON  ->  this runner  ->  evidence

The runner is deliberately dumb. It does not reason about the API. It sends
what the model asked for and compares the status code to the expectation the
model stated. Everything interesting happens when a case FAILS: that is a
hypothesis the API did not satisfy, and a human decides whether it is a defect.

Usage:
    python -m tests.runner                      # run everything
    python -m tests.runner TC-001 TC-012        # run specific cases
"""

import base64
import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
CASES = Path(__file__).resolve().parent.parent / "ai" / "generated_cases.json"

ACCOUNTS = {
    "alice": ("alice@corp.example", "alice123"),
    "bob": ("bob@corp.example", "bob123"),
}

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def login(client: httpx.Client, who: str) -> str:
    email, password = ACCOUNTS[who]
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def headers_for(client: httpx.Client, auth: str) -> dict:
    if auth in (None, "none"):
        return {}
    if auth == "garbage":
        return {"Authorization": "Bearer not-a-real-token!!"}
    if auth == "forged_admin":
        # We never asked the server for this. We made it up.
        forged = base64.urlsafe_b64encode(b"9:admin").decode()
        return {"Authorization": f"Bearer {forged}"}
    return {"Authorization": f"Bearer {login(client, auth)}"}


def send(client: httpx.Client, case: dict) -> httpx.Response:
    hdrs = headers_for(client, case.get("auth", "none"))
    url = BASE + case["endpoint"]
    method = case["method"].upper()
    if method == "GET":
        return client.get(url, params=case.get("query"), headers=hdrs)
    return client.post(url, json=case.get("payload"), headers=hdrs)


def evaluate(case: dict, resp: httpx.Response) -> tuple[str, str]:
    """Return (verdict, detail). PASS means the API behaved as the model expected."""
    expected = case.get("expect_status", [200, 201])
    body = resp.text

    if resp.status_code not in expected:
        return "FAIL", f"expected {expected}, got {resp.status_code}"

    forbidden = case.get("expect_body_not_contains")
    if forbidden and forbidden in body:
        return "FAIL", f"response leaked {forbidden!r}"

    return "PASS", f"{resp.status_code}"


def run(selected: list[str]) -> int:
    data = json.loads(CASES.read_text())
    cases = data["cases"]
    if selected:
        cases = [c for c in cases if c["id"] in selected]

    failures = []
    with httpx.Client(timeout=15.0) as client:
        client.post(f"{BASE}/_reset")
        print(f"\n{DIM}running {len(cases)} AI-generated cases against {BASE}{RESET}\n")

        for case in cases:
            try:
                for _ in range(case.get("repeat", 1)):
                    resp = send(client, case)
                verdict, detail = evaluate(case, resp)
            except Exception as exc:  # never abort the suite mid-demo
                resp = httpx.Response(599, text=f"transport error: {exc}")
                verdict, detail = "FAIL", "request could not complete"

            colour = GREEN if verdict == "PASS" else RED
            tag = f"[{case['severity'].upper()}]"
            print(f"{colour}{verdict:4}{RESET} {case['id']}  {tag:<10} {case['objective']}")
            if verdict == "FAIL":
                print(f"       {DIM}{detail}{RESET}")
                print(f"       {DIM}{resp.text[:160]}{RESET}")
                failures.append(case)

    print(f"\n{'-' * 72}")
    print(f"{len(cases) - len(failures)} matched expectation, "
          f"{RED}{len(failures)} did not{RESET}")
    if failures:
        print(f"\n{YELLOW}Candidate defects - a human still has to triage these:{RESET}")
        for c in failures:
            print(f"  {c['id']}  {c['severity']:<8} {c['potential_vulnerability']}")
    print()
    return len(failures)


if __name__ == "__main__":
    sys.exit(0 if run(sys.argv[1:]) == 0 else 1)
