"""Twenty people click Buy at the same moment on a workshop with 5 seats.

No single request is invalid here. Every one of these orders is something the
AI's test cases already declared correct. The defect only exists in the gap
between two of them, which is why a list of request/response pairs can never
contain it.

    python demo/race.py
"""

from concurrent.futures import ThreadPoolExecutor

import httpx

BASE = "http://127.0.0.1:8000"
TICKET = 3          # WORKSHOP-AI, stock 5
BUYERS = 20


def buy(_: int) -> int:
    with httpx.Client(timeout=30.0) as c:
        tok = c.post(f"{BASE}/auth/login",
                     json={"email": "alice@corp.example", "password": "alice123"}
                     ).json()["access_token"]
        r = c.post(f"{BASE}/orders",
                   json={"ticket_id": TICKET, "quantity": 1},
                   headers={"Authorization": f"Bearer {tok}"})
        return r.status_code


def main() -> None:
    with httpx.Client(timeout=30.0) as c:
        c.post(f"{BASE}/_reset")
        before = c.get(f"{BASE}/tickets", params={"q": "WORKSHOP"}).json()["results"][0]
    print(f"seats available before: {before['stock']}")
    print(f"buyers clicking at once: {BUYERS}\n")

    with ThreadPoolExecutor(max_workers=BUYERS) as pool:
        codes = list(pool.map(buy, range(BUYERS)))

    sold = codes.count(201)
    with httpx.Client(timeout=30.0) as c:
        after = c.get(f"{BASE}/tickets", params={"q": "WORKSHOP"}).json()["results"][0]

    print(f"orders accepted (201): {sold}")
    print(f"orders rejected (409): {codes.count(409)}")
    print(f"seats remaining after: {after['stock']}")
    print()
    if sold > before["stock"]:
        print(f"*** oversold by {sold - before['stock']} seats ***")
    else:
        print("stock held. no oversell on this run.")


if __name__ == "__main__":
    main()
